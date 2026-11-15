import React, {useEffect, useRef, useState} from 'react';

// Capture only: never opens QR destinations or starts an upload automatically.
export function CameraCapture({onCapture, disabled=false}:{onCapture:(file:File)=>void;disabled?:boolean}) {
  const video=useRef<HTMLVideoElement>(null), stream=useRef<MediaStream|null>(null);
  const generation=useRef(0);
  const [active,setActive]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState('');
  function release(){stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;if(video.current)video.current.srcObject=null;}
  function stop(){generation.current++;release();setActive(false);setPending(false);}
  useEffect(()=>{
    const hide=()=>{if(document.hidden)stop()};
    document.addEventListener('visibilitychange',hide);
    return()=>{generation.current++;release();document.removeEventListener('visibilitychange',hide)};
  },[]);
  async function start(){
    setError('');
    if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){setError('Camera unavailable. Use HTTPS and a supported browser, or upload a QR image.');return}
    const id=++generation.current;setPending(true);
    try{
      const media=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
      if(id!==generation.current){media.getTracks().forEach(track=>track.stop());return}
      stream.current=media;
      if(!video.current){release();return}
      video.current.srcObject=media;await video.current.play();
      if(id===generation.current)setActive(true);
    }catch{if(id===generation.current){release();setError('Camera access failed. Check permission or upload a QR image.')}}
    finally{if(id===generation.current)setPending(false)}
  }
  function capture(){
    const source=video.current;
    if(!source?.videoWidth||!source.videoHeight){setError('Camera is not ready. Try again.');return}
    const canvas=document.createElement('canvas');
    const scale=Math.min(1,1280/Math.max(source.videoWidth,source.videoHeight));
    canvas.width=Math.max(1,Math.round(source.videoWidth*scale));canvas.height=Math.max(1,Math.round(source.videoHeight*scale));
    const context=canvas.getContext('2d');
    if(!context){setError('Image capture failed. Upload a QR image instead.');return}
    context.drawImage(source,0,0,canvas.width,canvas.height);
    const id=generation.current;
    canvas.toBlob(blob=>{if(id!==generation.current)return;if(!blob){setError('Image capture failed. Upload a QR image instead.');return}stop();onCapture(new File([blob],'camera-qr.jpg',{type:'image/jpeg'}))},'image/jpeg',0.9);
  }
  return <section className="camera-capture"><h3>Scan with your camera</h3><p>Camera access starts only when you allow it. Capture one frame, then choose Analyze file to upload it. No audio is recorded.</p><video ref={video} muted playsInline aria-label="Camera preview" hidden={!active}/>{error&&<p className="error-box" role="alert">{error}</p>}<div className="camera-actions">{!active&&!pending&&<button type="button" className="btn secondary" disabled={disabled} onClick={start}>Enable camera</button>}{active&&<button type="button" className="btn secondary" disabled={disabled} onClick={capture}>Capture QR image</button>}{(active||pending)&&<button type="button" className="btn secondary" onClick={stop}>Stop camera</button>}</div><p>QR destinations are never opened automatically. A QR code cannot verify that money was received.</p></section>;
}
