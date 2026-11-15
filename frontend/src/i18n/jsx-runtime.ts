import{jsx as originalJSX,jsxs as originalJSXs,Fragment}from'react/jsx-runtime';
import{localized}from'./host';
export{Fragment};
export const jsx:typeof originalJSX=(type,props,key)=>originalJSX(type,localized(type,props),key);
export const jsxs:typeof originalJSXs=(type,props,key)=>originalJSXs(type,localized(type,props),key);
export type{JSX}from'react/jsx-runtime';
