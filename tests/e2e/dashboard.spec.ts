import {test,expect} from '../../apps/web/node_modules/@playwright/test';
import AxeBuilder from '../../apps/web/node_modules/@axe-core/playwright';
import fs from 'node:fs';
const vars=Object.fromEntries(fs.readFileSync(process.env.E2E_ENV_FILE||'.local/dev.env','utf8').trim().split('\n').map(l=>{const i=l.indexOf('=');return[l.slice(0,i),l.slice(i+1)]}));
test('login, navigation, event recognition and responsive dashboard',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByLabel('E-mail',{exact:true}).fill(vars.ADMIN_EMAIL);await page.getByLabel('Senha',{exact:true}).fill(vars.ADMIN_PASSWORD);await page.getByRole('button',{name:'Entrar no ConfigSentinel'}).click();await expect(page.getByRole('heading',{name:'Visão geral'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Atividade recente'})).toBeVisible();
 const a11y=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(a11y.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))).toEqual([]);
 await page.screenshot({path:'.local/dashboard-desktop.png',fullPage:true});
 if(await page.locator('.event-button').count()){await page.locator('.event-button').first().click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByLabel('Comentário de investigação').fill('Reconhecimento sintético confirmado pelo navegador.');await page.getByRole('button',{name:'Reconhecer evento',exact:true}).click();await expect(page.getByText('Reconhecimento sintético confirmado pelo navegador.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Fechar',exact:true}).click()}
 for(const [link,heading]of [['Eventos','Histórico de eventos'],['Servidores','Servidores'],['Projetos e ambientes','Projetos e ambientes'],['Credenciais','Credenciais de agentes'],['Membros','Membros e permissões'],['Auditoria','Trilha de auditoria']]){await page.getByRole('navigation').getByRole('link',{name:link,exact:true}).click();await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0)}
 await page.getByRole('navigation').getByRole('link',{name:'Visão geral',exact:true}).click();await page.setViewportSize({width:390,height:844});await page.screenshot({path:'.local/dashboard-mobile.png',fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();expect(errors).toEqual([]);
});
