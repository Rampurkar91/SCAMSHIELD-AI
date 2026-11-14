import{tr}from'./core';
// Translate only rendered host UI, never data/state/API enum values or input values.
// Raw evidence containers opt out with translate="no"; code/pre are always untouched.
export function localized(type:unknown,props:any){
 if(typeof type!=='string'||!props||props.translate==='no'||['pre','code','textarea','script','style'].includes(type))return props;
 const next={...props};
 for(const key of['placeholder','title','aria-label','alt'])if(typeof next[key]==='string')next[key]=tr(next[key]);
 if(type==='input'){if(typeof props.placeholder==='string')next.placeholder=tr(props.placeholder);return next}
 const convert=(value:any):any=>typeof value==='string'?tr(value):Array.isArray(value)?value.map(convert):value;
 // Option text may translate; submitted values must remain the original backend enums.
 if(type==='option'&&next.value===undefined&&typeof props.children==='string')next.value=props.children;
 next.children=convert(props.children);
 return next;
}
