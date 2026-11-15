import {useSyncExternalStore} from 'react';
import hi from './hi.json';
import mr from './mr.json';
export type Locale='en'|'hi'|'mr';
const dictionaries:Record<Locale,Record<string,string>>={en:{},hi,mr};
let locale:Locale=typeof localStorage!=='undefined'&&['en','hi','mr'].includes(localStorage.getItem('locale')||'')?localStorage.getItem('locale') as Locale:'en';
const listeners=new Set<()=>void>();
export function setLocale(next:Locale){locale=next;localStorage.setItem('locale',next);document.documentElement.lang=next;listeners.forEach(l=>l())}
export function getLocale(){return locale}
export function useLocale(){return useSyncExternalStore(l=>{listeners.add(l);return()=>{listeners.delete(l)}},getLocale,()=> 'en' as Locale)}
export function tr(value:string):string{
 if(locale==='en')return value;
 const key=value.replace(/\s+/g,' ').trim();
 if(!key)return value;
 const translated=dictionaries[locale][key];
 if(translated)return value.replace(value.trim(),translated);
 const rules:[RegExp,string][]=[[/^Welcome back, (.+)$/,'Welcome back, {name}'],[/^(\d+) records · Page (\d+)$/,'{count} records · Page {page}'],[/^Page (\d+)$/,'Page {page}']];
 for(const[pattern,template]of rules){const match=key.match(pattern);const text=dictionaries[locale][template];if(match&&text)return text.replace('{name}',match[1]).replace('{count}',match[1]).replace('{page}',match[2]||match[1])}
 return value;
}
