按涨停板数量排序： 
select code, count(code) as cc from  ztzb where day > 20220301 group by code  having cc > 5 order by cc desc


select avg(`1日收盘涨幅`) from ztzb where day >= 20220828 and 第几板 = 2
平均炸板率: 30%
平均涨停后隔日最高涨幅：5%
平均涨停后隔日收盘涨幅：1%

二板平均涨停后隔日最高涨幅：6%
二板平均涨停后隔日收盘涨幅：1%

平均炸板后隔日最高涨幅：2%
平均炸板后隔日收盘涨幅：-1%


select count(*) from ztzb where day >= 20220828 and 第几板 = 1 and tag = 'ZB' and  "1日最高涨幅" >= -11 and "1日最高涨幅" < 0

