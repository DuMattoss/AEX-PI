const toggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navegacao');
toggle?.addEventListener('click', () => { const open = toggle.getAttribute('aria-expanded') !== 'true'; toggle.setAttribute('aria-expanded', String(open)); navigation.hidden = !open; });
document.addEventListener('keydown', event => { if(event.key === 'Escape' && navigation && !navigation.hidden){navigation.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();} });
document.querySelector('#print-report')?.addEventListener('click', () => window.print());
const sale = document.querySelector('.sale-form');
function totalSale(){
  let cents = 0;
  sale?.querySelectorAll('.classification-row').forEach(row => {
    const peso = Math.round(Number(row.querySelector('.peso').value || 0) * 100);
    const preco = Math.round(Number(row.querySelector('.preco').value || 0) * 100);
    if(peso > 0 && preco > 0) cents += Math.round(peso * preco / 100);
  });
  if(sale) document.querySelector('#sale-total').textContent = (cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
}
sale?.addEventListener('input',totalSale); totalSale();
// Gráfico local em Canvas: sem CDN e com tabela acessível dos mesmos dados.
const canvas = document.querySelector('#material-chart');
if(canvas){
  const data = JSON.parse(document.querySelector('#chart-data').textContent);
  const colors = ['#176345','#b5894e','#738c96'];
  function draw(){
    const box=canvas.parentElement.getBoundingClientRect(), dpr=window.devicePixelRatio||1;
    canvas.width=box.width*dpr;canvas.height=box.height*dpr;
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
    const w=box.width,h=box.height,left=w<450?48:65,right=14,top=16,bottom=34;
    const max=Math.max(1,...data.series.flatMap(s=>s.valores))*1.15;
    ctx.font='11px Arial';ctx.textAlign='right';ctx.fillStyle='#596e63';
    for(let i=0;i<=4;i++){const y=top+(h-top-bottom)*i/4;ctx.strokeStyle='#e9e5db';ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(w-right,y);ctx.stroke();ctx.fillText((max*(4-i)/4).toLocaleString('pt-BR',{maximumFractionDigits:0}),left-8,y+4);}
    ctx.textAlign='center';data.meses.forEach((m,i)=>{const stride=Math.max(1,Math.ceil(data.meses.length/(w<450?6:12)));if(i%stride!==0&&i!==data.meses.length-1)return;ctx.fillText(m,left+(w-left-right)*i/(data.meses.length-1),h-10);});
    data.series.forEach((serie,j)=>{ctx.strokeStyle=colors[j];ctx.fillStyle=colors[j];ctx.lineWidth=2;ctx.beginPath();serie.valores.forEach((v,i)=>{const x=left+(w-left-right)*i/(data.meses.length-1),y=h-bottom-v/max*(h-top-bottom);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();serie.valores.forEach((v,i)=>{ctx.beginPath();ctx.arc(left+(w-left-right)*i/(data.meses.length-1),h-bottom-v/max*(h-top-bottom),3,0,Math.PI*2);ctx.fill();});});
  }
  new ResizeObserver(draw).observe(canvas.parentElement);
}
