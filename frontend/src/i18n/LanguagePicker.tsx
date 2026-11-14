import React,{useState}from'react';
import{Globe}from'lucide-react';
import{useLocale,setLocale,type Locale}from'./core';
import{api}from'../api';
export function LanguagePicker(){const locale=useLocale(),[error,setError]=useState(false);async function change(next:Locale){setLocale(next);setError(false);if(sessionStorage.getItem('token')){try{await api.put('/profile/preferences',{language:next})}catch{setError(true)}}}return <div className="locale-switch"><Globe size={15}/><label htmlFor="ui-language" className="sr-only">Interface language</label><select id="ui-language" value={locale} onChange={e=>change(e.target.value as Locale)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="mr">मराठी</option></select>{error&&<span role="status">Language changed locally; account preference could not be saved.</span>}</div>}
