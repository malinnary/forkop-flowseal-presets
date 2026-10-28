'use strict';
'require view';
'require fs';
'require ui';
'require poll';
return view.extend({
 load: function() {
  return Promise.all([fs.read('/usr/share/forkop-flowseal/catalog.txt'),
   fs.exec('/usr/sbin/flowseal-presets', ['status'])]);
 },
 render: function(data) {
  var names=data[0].trim().split(/\s+/), active=(data[1].stdout||'inactive').trim();
  var select=E('select',{'class':'cbi-input-select'},names.map(function(name){
   return E('option',{value:name,selected:active===name?'selected':null},name);
  }));
  var status=E('p',{},'Активный пресет: '+active), output=E('pre',{'style':'white-space:pre-wrap;max-height:25em;overflow:auto;'});
  var buttons=[];
  function run(action) {
   buttons.forEach(function(button){button.disabled=true;});
   status.textContent='Выполняется '+action+'… Не закрывайте страницу. Подключения могут прерваться.';
   var args=['start',action,action==='restore'?'':select.value];
   return fs.exec('/usr/sbin/flowseal-presets',args).then(function(result){
    output.textContent=(result.stdout||'')+'\n'+(result.stderr||'');
    if(result.code!==0)throw new Error('Команда завершилась с кодом '+result.code+'. Подробности ниже.');
    status.textContent='Задание запущено в фоне.';
   }).catch(function(error){status.textContent=String(error);buttons.forEach(function(button){button.disabled=false;});})
    ;
  }
  function button(label,action) {
   var b=E('button',{'class':'cbi-button',click:function(){
    if(action==='check')return run(action);
    ui.showModal('Подтверждение',[
     E('p',{},action==='restore'?'Вернуть настройки Forkop, сохранённые до первого применения?':'Применить '+select.value+'? Это экспериментальная адаптация; качество обхода не гарантируется.'),
     E('div',{'class':'right'},[
      E('button',{'class':'cbi-button',click:ui.hideModal},'Отмена'),' ',
      E('button',{'class':'cbi-button cbi-button-apply',click:function(){ui.hideModal();run(action);}},'Продолжить')])]);
   }},label);buttons.push(b);return b;
  }
  poll.add(function(){return Promise.all([
   fs.read('/tmp/flowseal-job.status').catch(function(){return '';}),
   fs.read('/tmp/flowseal-job.log').catch(function(){return '';})
  ]).then(function(values){
   var state=values[0].trim();if(!state)return;
   output.textContent=values[1];
   buttons.forEach(function(button){button.disabled=state==='running';});
   if(state==='running'){status.textContent='Применение в фоне…';return;}
   return fs.exec('/usr/sbin/flowseal-presets',['status']).then(function(current){
    status.textContent=(state==='success'?'Готово. ':'Ошибка — см. журнал. ')+'Активный пресет: '+(current.stdout||'').trim();
   });
  });},3);
  return E('div',{},[
   E('h2',{},'Flowseal для Forkop — экспериментальная версия'),
   E('p',{},'22 варианта для YouTube и Discord. Общие правила Flowseal для других сайтов и игр не включены.'),
   E('p',{},'Неофициальная адаптация Flowseal/zapret-discord-youtube (zapret: bol-van). Ровно две постоянные секции: YouTube и Discord; один выбор меняет обе.'),
   E('p',{},'Первая установка требует чистого Forkop. Изменённые вручную настройки не перезаписываются. Автозапуск не включается автоматически.'),
   select,' ',button('Проверить','check'),' ',button('Применить','apply'),' ',button('Откатить','restore'),status,output
  ]);
 },
 handleSaveApply:null,handleSave:null,handleReset:null
});
