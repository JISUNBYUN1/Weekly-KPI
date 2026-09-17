"""Import cached actual values only. Does not modify operational JSONs."""
import json,re,sys,hashlib
from pathlib import Path
import openpyxl
AGENCIES=['평강','문성','케이디엘','하나로','회산','현성','클릭나라']
def build(source,destination):
 w=openpyxl.load_workbook(source,read_only=True,data_only=True)
 out=Path(destination);out.mkdir(parents=True,exist_ok=True)
 def save(name,data): (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
 datasets={};checks=[]
 for sheet,name,pcol,acol in [('⑥ SOP_AI Live효율','live_commerce_data.json',2,3),('⑦ SOP 어필리에이트 현황','affiliate_data.json',1,2)]:
  rows=list(w[sheet].values); data={'월별':{},'주차별':{}}
  for i,r in enumerate(rows):
   label=str(r[pcol] or ''); m=re.match(r'^(\d+)月$',label) or re.match(r'^(\d+)월$',label);wk=re.match(r'^(?:W)?(\d+)([AB]?)(?:주차|$)',label)
   if r[acol]!='계' or not (m or wk): continue
   if wk and int(wk[1])>37: continue
   key=f'{int(m[1])}월' if m else f'W{int(wk[1]):02d}{wk[2]}'
   scope='월별' if m else '주차별'; bucket={}
   for rr in rows[i+1:i+8]:
    a=rr[acol]
    if a not in AGENCIES: raise ValueError((sheet,i,a))
    if name.startswith('live'):
     bucket[a]={'방송횟수':rr[4],'방송매출':rr[7]}
    else:
     bucket[a]={}
     for channel,cols in [('쇼핑커넥트',{'크리에이터운영수':7,'운영모델':8,'유입수':9,'상품주문건수':10,'주문금액':12}),('공동구매',{'크리에이터운영수':13,'운영모델':14,'상품주문건수':15,'주문금액':16})]:
      v={k:rr[c] if isinstance(rr[c],(int,float)) else 0 for k,c in cols.items()}
      if v['주문금액'] is not None:v['주문금액']=round(v['주문금액']*1e6)
      v['전환율']=100*v['상품주문건수']/v['유입수'] if v.get('유입수') and v.get('상품주문건수') is not None else None
      bucket[a][channel]=v
   data[scope][key]=bucket
   total=sum(v['방송매출'] for v in bucket.values()) if name.startswith('live') else sum(v[c]['주문금액'] for v in bucket.values() for c in v)
   expected=r[7] if name.startswith('live') else round(r[6]*1e6)
   checks.append({'sheet':sheet,'period':key,'source_total':expected,'imported_total':total,'difference':total-expected})
  datasets[name]=data;save(name,data)
 rows=list(w['③ SOP_스토어_고객변화'].values)
 smart={k:{'월별':{},'주차별':{}} for k in ['신규관심고객','구매비중']}
 periods=[('월별',f'{m}월',c) for m,c in enumerate([6,9,12,15,18,21,42,63,84],1)]
 for c,value in enumerate(rows[6],1):
  match=re.match(r'^(\d+)([AB]?)(?:주|\()',str(value or ''))
  if match and int(match[1])<=37: periods.append(('주차별',f'W{int(match[1]):02d}{match[2]}',c))
 for scope,key,c in periods:
  for section in smart:smart[section][scope][key]={}
  for j,a in enumerate(AGENCIES):
   r=rows[9+j];value=r[c] if scope=='월별' else r[c-1]
   interest={'신규관심고객수':value}
   if scope=='월별':interest['누적관심고객수']=r[c-1]
   smart['신규관심고객'][scope][key][a]=interest
   new,repeat=rows[23+j][c],rows[31+j][c]
   valid=all(isinstance(v,(float,int)) and v>=0 for v in [new,repeat]); total=new+repeat if valid else 0
   smart['구매비중'][scope][key][a]={'신규구매고객수':new,'재구매고객수':repeat,'신규구매비중':new/total*100 if total else None,'재구매비중':repeat/total*100 if total else None}
 save('smartstore_data.json',smart)
 history=[];week=None;period=''
 for r in w['④ 파트너별_주요활동'].values:
  m=re.match(r'(\d+)주차',str(r[1] or ''))
  if m:week=f'W{int(m[1]):02d}';period=r[1]
  if week and r[2] in AGENCIES:
   history.append({'거래선':r[2],'주차':week,'기간':period,'주요활동':str(r[4] or ''),'후속조치':str(r[5] or '')})
 save('activity_history.json',history)
 # Business week 1 is Jan 1-4; split at month boundaries.
 from datetime import date,timedelta
 calendar={};start=date(2026,1,1);n=1
 while start.year==2026:
  end=min(start+timedelta(days=6-start.weekday()),date(2026,12,31))
  calendar[f'W{n:02d}']={'start':start.strftime('%m/%d'),'end':end.strftime('%m/%d'),'month':start.month if start.month==end.month else [start.month,end.month]}
  start=end+timedelta(days=1);n+=1
 save('weeks_2026.json',calendar)
 save('manifest.json',{'source':Path(source).name,'sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'closed_week':'W37','closed_date':'2026-09-13','checks':checks,'activity_records':len(history),'star_note':'既存 STAR 유지: 첨부 W37 피벗은 실판매 수량이며 셀인·셀아웃 금액의 대체 원본이 아님'})
 return checks
if __name__=='__main__':
 checks=build(sys.argv[1],sys.argv[2]);print(json.dumps(checks,ensure_ascii=False))
