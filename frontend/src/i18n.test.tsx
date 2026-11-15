import React from'react';
import{describe,it,expect,afterEach}from'vitest';
import'@testing-library/jest-dom/vitest';
import{render,screen,cleanup}from'@testing-library/react';
import{setLocale,tr}from'./i18n/core';
import{localized}from'./i18n/host';
import hi from'./i18n/hi.json';import mr from'./i18n/mr.json';import sources from'./i18n/source-messages.json';
afterEach(()=>{cleanup();setLocale('en')});
describe('local UI localization',()=>{
 it('renders Hindi through the actual JSX runtime',()=>{setLocale('hi');render(<h1>Family safety</h1>);expect(screen.getByRole('heading')).toHaveTextContent('परिवार की सुरक्षा')});
 it('supports Marathi and dynamic greetings',()=>{setLocale('mr');expect(tr('Welcome back, Asha')).toBe('पुन्हा स्वागत आहे, Asha');render(<button>Send verification email</button>);expect(screen.getByRole('button')).toHaveTextContent('पडताळणी ईमेल पाठवा')});
 it('never changes submitted enum values or raw evidence',()=>{setLocale('hi');expect(localized('option',{children:'Under Review'})).toEqual({children:'समीक्षाधीन',value:'Under Review'});expect(localized('pre',{children:'Family safety'}).children).toBe('Family safety');expect(localized('p',{translate:'no',children:'Family safety'}).children).toBe('Family safety');expect(localized('input',{value:'Password',placeholder:'Password'}).value).toBe('Password')});
 it('keeps source catalog keys in both languages',()=>{const exclusions=new Set(['1px solid #293a52','sidebar open','English','Hindi','Marathi']);for(const source of sources.filter(s=>!exclusions.has(s))){expect(hi,source).toHaveProperty(source);expect(mr,source).toHaveProperty(source)}});
});
