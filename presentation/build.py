"""Build the narrated presentation package. Run with PYTHONPATH=.presentation-tools."""
from pathlib import Path
import subprocess, re, zipfile, textwrap
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'deliverables'; OUT.mkdir(exist_ok=True)
FRAMES=ROOT/'frames'; FRAMES.mkdir(exist_ok=True)
BG='#091525'; CARD='#12253A'; WHITE='#EDF5FF'; MUTED='#ABC0D5'; TEAL='#42DED0'; BLUE='#79AFFF'
slides=[
('PROJECT OVERVIEW','SCAMSHIELD AI','Pause. Inspect. Protect.',[
('Purpose','Multilingual scam awareness and evidence-based risk analysis.'),('Experience','Understand suspicious content before taking action.'),('Important','Risk estimates support investigation; they never guarantee safety.')], 'Project presentation • Illustrated workflows, not a live website recording'),
('THE PROBLEM','Pressure creates risk','Help users slow down and verify independently.',[
('Suspicious communication','Messages, links and email can impersonate trusted organizations.'),('Payment confusion','QR codes and screenshots cannot prove a payment was received.'),('Responsible response','Explain indicators and limitations instead of promising certainty.')], 'A score from 0–100 is not a fraud probability'),
('SYSTEM DESIGN','One connected workflow','React interface → FastAPI services → owned records',[
('User interface','Responsive React application with English, Hindi and Marathi UI.'),('Application services','Authenticated scanning, history, reports and profile workflows.'),('Data and access','Database-backed records with ownership checks and account protection.')], 'Architecture illustration • No live deployment is claimed'),
('CORE ANALYSIS','From content to evidence','Submit → Inspect → Explain → Verify',[
('Supported inputs','Messages, email text, URLs and UPI instructions.'),('Readable results','Detected indicators, estimated risk and practical safety actions.'),('Independent checks','Optional reputation and AI services require configuration and consent.')], 'No threat-database match does not establish safety'),
('VISUAL WORKFLOWS','Images and QR codes','Inspect a payload without opening its destination.',[
('OCR','Extract image text using installed Tesseract language packs.'),('Camera capture','Permission → one frame → separate Analyze file action.'),('Safe handling','Stop camera tracks; do not automatically navigate to QR destinations.')], 'Manual capture, not continuous decoding • Physical-camera test pending'),
('ADVANCED ANALYSIS','Voice and developer tools','Useful signals, with explicit boundaries.',[
('Voice recordings','Authorized PCM WAV → installed local speech model → transcript analysis.'),('Source archives','Bounded static ZIP inspection; uploaded code is not executed.'),('Limitations','Transcription is not deepfake detection. Static rules are not a full audit.')], 'Local software and speech-model files must be installed'),
('PRIVACY FIRST','Family safety by consent','Membership does not expose private scan history.',[
('Verify and invite','Verified email; recipient-bound invitation; explicit acceptance.'),('Choose a summary','Share a selected scan’s type, score, risk level and sharing time.'),('Keep control','Separate consent per share; leave groups or revoke access.')], 'Original messages, URLs and private scan details are not shared'),
('DEPLOYMENT OVERVIEW','Separate the scanner','Deployment setup illustration — not a live hosting dashboard',[
('Browser → API → database','Frontend calls the authenticated API; records remain access-controlled.'),('API → isolated worker','Production file scans require a separate authenticated worker.'),('Worker boundary','Resource limits, restricted network and read-only container configuration.')], 'Production file scanning fails closed when the worker is missing'),
('OPERATIONS & VALIDATION','Configure. Test. Observe.','Configured is not the same as verified.',[
('Owner configuration','Provider keys, SMTP settings, OCR packs and speech-model weights.'),('Recorded checks','47 backend tests • 24 frontend tests • TypeScript • production build.'),('Operator verification','Test cloud hosting, PostgreSQL, SMTP, live providers and physical camera.')], 'Admin diagnostics show status without exposing credential values'),
('ROADMAP & TAKEAWAY','Safer decisions, not guarantees','Verify independently. Protect credentials. Pause before paying.',[
('Built foundation','Scanning workflows, private history, family consent and multilingual UI.'),('Next phases','Report attachments, retention controls, audit logs and distributed limits.'),('Safety reminder','Never share passwords, OTPs or a UPI PIN. Verify using official channels.')], 'Thank you • ScamShield AI project presentation')
]
durations=[20,20,20,15,15,15,15,20,20,20]
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def ft(size,b=False):return ImageFont.truetype(bold if b else font,size)
def wrap(draw,text,x,y,width,size,color,b=False):
    words=text.split();line=''
    for word in words:
        trial=(line+' '+word).strip()
        if draw.textlength(trial,font=ft(size,b))>width and line:
            draw.text((x,y),line,font=ft(size,b),fill=color);y+=int(size*1.45);line=word
        else:line=trial
    if line:draw.text((x,y),line,font=ft(size,b),fill=color);y+=int(size*1.45)
    return y
prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
def color(hex):return RGBColor.from_string(hex.lstrip('#'))
def box(sl,x,y,w,h,fill):
    sh=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=color(fill);sh.line.fill.background();return sh

def txt(sl,text,x,y,w,h,size=18,c=WHITE,b=False):
    shape=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=shape.text_frame;tf.word_wrap=True
    p=tf.paragraphs[0];p.text=text;p.font.name='Aptos';p.font.size=Pt(size);p.font.bold=b;p.font.color.rgb=color(c)
    return shape
for n,(section,title,subtitle,cards,footer) in enumerate(slides,1):
    im=Image.new('RGB',(1280,720),BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,1280,7),fill=TEAL)
    d.text((55,32),'SCAMSHIELD AI  /  '+section,font=ft(17,True),fill=TEAL)
    d.text((1130,32),f'{n:02d} / 10',font=ft(17),fill=MUTED)
    d.text((55,96),title,font=ft(49,True),fill=WHITE)
    wrap(d,subtitle,58,166,1150,23,MUTED)
    for k,(heading,body) in enumerate(cards):
        x=55+k*398
        d.rounded_rectangle((x,258,x+376,568),radius=16,fill=CARD)
        d.text((x+22,281),f'0{k+1}',font=ft(24,True),fill=TEAL)
        y=wrap(d,heading,x+22,335,331,24,WHITE,True)
        wrap(d,body,x+22,y+17,331,21,MUTED)
    wrap(d,footer,58,619,1150,17,BLUE)
    d.rectangle((55,685,1225,689),fill=CARD);d.rectangle((55,685,55+1170*n/10,689),fill=TEAL)
    im.save(FRAMES/f'slide-{n:02d}.png')
    sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.background.fill.solid();sl.background.fill.fore_color.rgb=color(BG)
    box(sl,0,0,13.333,.06,TEAL)
    txt(sl,'SCAMSHIELD AI  /  '+section,.55,.28,11,.35,12,TEAL,True)
    txt(sl,f'{n:02d} / 10',11.9,.28,1,.35,12,MUTED)
    txt(sl,title,.55,.92,12.1,.8,31,WHITE,True)
    txt(sl,subtitle,.58,1.72,12.1,.7,16,MUTED)
    for k,(heading,body) in enumerate(cards):
        x=.55+k*4.15;box(sl,x,2.68,3.92,3.23,CARD)
        txt(sl,f'0{k+1}',x+.22,2.88,3,.4,18,TEAL,True)
        txt(sl,heading,x+.22,3.4,3.44,.7,19,WHITE,True)
        txt(sl,body,x+.22,4.18,3.44,1.4,16,MUTED)
    txt(sl,footer,.58,6.42,12.2,.65,12,BLUE)
    sl.notes_slide.notes_text_frame.text='Presentation illustration, not a live website recording. '+footer
prs.save(OUT/'ScamShield_AI_10_Slide_Presentation.pptx')
f=imageio_ffmpeg.get_ffmpeg_exe()
def run(args):subprocess.run([f,'-hide_banner','-loglevel','error','-y',*args],check=True)
for i in range(1,4):
    src=ROOT/'audio'/f'part-{i}.mp3'
    r=subprocess.run([f,'-i',str(src)],capture_output=True,text=True)
    h,m,s=map(float,re.search(r'Duration: (\d+):(\d+):([\d.]+)',r.stderr).groups());duration=h*3600+m*60+s
    tempo=max(1,duration/59.8)
    run(['-i',str(src),'-af',f'atempo={tempo:.6f},apad','-t','60','-ar','48000','-ac','2',str(ROOT/'audio'/f'timed-{i}.wav')])
concat=ROOT/'audio'/'concat.txt';concat.write_text(''.join(f"file '{ROOT / 'audio' / f'timed-{i}.wav'}'\n" for i in range(1,4)))
run(['-f','concat','-safe','0','-i',str(concat),'-c:a','pcm_s16le',str(ROOT/'audio'/'narration.wav')])
frames=FRAMES/'timeline.txt';frames.write_text(''.join(f"file '{FRAMES/f'slide-{i:02d}.png'}'\nduration {dur}\n" for i,dur in enumerate(durations,1))+f"file '{FRAMES/'slide-10.png'}'\n")
run(['-f','concat','-safe','0','-i',str(frames),'-i',str(ROOT/'audio'/'narration.wav'),'-t','180','-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','fast','-crf','22','-c:a','aac','-b:a','160k','-movflags','+faststart',str(OUT/'ScamShield_AI_3_Minute_Demo.mp4')])
(OUT/'READ_ME.txt').write_text('SCAMSHIELD AI — PRESENTATION PACKAGE\n\n1. ScamShield_AI_3_Minute_Demo.mp4: 180-second, 1280x720 narrated project overview.\n2. ScamShield_AI_10_Slide_Presentation.pptx: editable 10-slide presentation.\n\nNarration: English, AI-generated voice.\nVisuals: project workflow and architecture illustrations, NOT a screen recording or proof of a live deployment. No public deployment URL was supplied. The deployment section explains service layout and required configuration.\n\nFeatures and recorded test counts are based on docs/PROGRESS.md in the project repository. Tests were recorded during development, not rerun as part of media generation. No private credentials, actual user evidence, or tokens are included.\n\nRemaining requirements include live SMTP/provider verification, speech model setup, cloud/PostgreSQL/container verification, and physical camera testing. Risk estimates are not fraud probabilities or guarantees.\n')
archive=OUT/'ScamShield_AI_Presentation_Package.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in OUT.iterdir():
        if path.suffix!='.zip':z.write(path,path.name)
print(archive)
