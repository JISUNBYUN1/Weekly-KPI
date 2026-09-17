"""Compact performance overview: two charts, three actionable highlights."""
import pandas as pd
from report_data import display_number,read_file

def render_brief(st,root,rows,previous,live,activities,calendar,month,week,monthly,star,prior,partial):
 from executive_report import (AGENCIES,business_week_to_star_label,star_partner_totals,
   tailored_sop_actions,weeks_for_month,number,_latest_activity,_brief_activity)
 scope='월별' if monthly else '주차별';period=month if monthly else business_week_to_star_label(week)
 prev=prior if monthly else business_week_to_star_label(prior) if prior else None
 st.subheader('성과 한눈에 보기')
 left,right=st.columns(2)
 with left:
  st.caption('SOP 7개 거래선 · 셀인 / 셀아웃 (억원) · 기존 STAR 기준')
  values=[{'거래선':a,**{k.replace('_금액',''):v/1e8 for k,v in star_partner_totals(star,scope,period,a).items() if k.endswith('_금액')}} for a in AGENCIES] if star else []
  if values:st.bar_chart(pd.DataFrame(values).set_index('거래선'),height=260)
  else:st.info('STAR 실적 없음')
 with right:
  efficiency=[{'거래선':r['거래선'],'회당 매출(만원)':r['라이브 매출(백만)']*100/r['방송횟수']} for r in rows if number(r['라이브 매출(백만)']) and number(r['방송횟수']) and r['방송횟수']>0]
  st.caption('라이브 효율 · 회당 매출 (만원)')
  if efficiency:st.bar_chart(pd.DataFrame(efficiency).set_index('거래선'),height=260)
 st.subheader('이번 기간 우선 실행')
 activity_scope=set(weeks_for_month(calendar,month)) if monthly else week
 # Rank using observed channel changes; concise first view, evidence on demand.
 before={r['거래선']:r for r in previous}; signals=[]
 for r in rows:
  a=r['거래선']; old=before.get(a,{})
  for field,label in [('라이브 매출(백만)','라이브'),('어필리에이트 주문금액(백만)','어필리에이트'),('신규 관심고객','관심고객')]:
   current=r.get(field); last=old.get(field)
   if not number(current):continue
   delta=current-last if number(last) else None
   score=abs(delta)/max(abs(last),1) if delta is not None else abs(current)
   signals.append((score,a,label,current,delta))
 selected=[];seen=set()
 for item in sorted(signals,reverse=True):
  if item[2] not in seen: selected.append(item);seen.add(item[2])
 for col,item in zip(st.columns(3),selected):
  _,a,label,current,delta=item
  money=label!='관심고객';unit='억원' if money else '명';scale=100 if money else 1
  linked,origin=_latest_activity(activities,a,activity_scope)
  evidence=_brief_activity(linked,limit=110,keywords=('라이브','방송') if label=='라이브' else ('커넥트','공구','공동') if label=='어필리에이트' else ('알림','고객','광고'))
  if label == '라이브':
   now=next(x for x in rows if x['거래선']==a);old=before.get(a,{})
   nc,oc=now.get('방송횟수'),old.get('방송횟수')
   improving=(number(nc) and nc>0 and number(oc) and oc>0 and number(old.get('라이브 매출(백만)')) and current/nc>old['라이브 매출(백만)']/oc)
   action=('회당 매출 개선: 현재 상품·시간대 조합을 유지하고 상위 모델 1개에 추가 편성 검토' if improving else
           '방송 확대 전 회당 매출 하위 편성 1회를 축소하고, 상위 시간대·모델 조합으로 전환 제안')
  elif label == '어필리에이트':
   action=('음수 주문금액: 취소·환불 반영분과 신규 주문을 분리 확인한 뒤 크리에이터별 순매출 기준 집행 재검토' if current<0 else
           '주문금액 증가: 상위 크리에이터의 판매 모델·콘텐츠를 재활용하여 유사 고객층에 1건 추가 노출 검토' if delta is not None and delta>0 else
           '주문금액 둔화: 크리에이터별 유입·전환·취소율을 분리하고, 유입 대비 주문이 낮은 콘텐츠 1건 수정 제안')
  else:
   action=('관심고객 순감: 알림 해제·혜택 종료 경로를 확인하고 기존 고객 대상 메시지 빈도와 혜택 재설계 검토' if current<0 else
           '관심고객 순증: 유입 고객에게 첫 구매 혜택 1건을 노출하고 다음 주 신규 구매 전환을 추적 제안')
  with col:
   st.markdown(f'**{a} · {label}**')
   st.metric('기간 실적 ('+unit+')',display_number(current/scale),display_number(delta/scale,signed=True)+unit if delta is not None else None)
   st.caption(origin+' · '+(evidence[:52]+'…' if len(evidence)>52 else evidence))
   st.markdown('**제안** · '+action)
   with st.expander('활동 근거 · 성과 연결'):
    st.write(origin+' · '+evidence)
    st.caption('동기간 관측에 따른 실행 가설 · 활동별 주문 연결 자료 없이는 인과관계 확정 불가')
 with st.expander('거래선별 상세 실행안'):
  proposals=tailored_sop_actions(star,scope,period,None if partial else prev,rows,previous,activities,activity_scope,monthly) if star else []
  for p in proposals:
   st.markdown('**'+p['거래선']+' · '+p['핵심 신호']+'**')
   st.write(p['차월 실행 제안' if monthly else '차주 실행 제안'])
   st.caption(p['활동 근거']+' · '+p['확인 KPI'])
 with st.expander('자료 기준'):
  st.write('마케팅·활동: W37 취합본 / 9월은 9월 13일까지. 셀인·셀아웃 금액: 기존 STAR 원본 유지. W37 첨부의 수량 피벗으로 금액을 대체하지 않았습니다.')
  st.write('총액은 억원 정수, 회당 매출은 만원 정수. 반올림 시 0이 되는 유효값은 <1로 표시합니다. 음수는 △, 증가는 +입니다.')
