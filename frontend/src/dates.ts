/** 返回本地时区的“今天”日期字符串（YYYY-MM-DD）。
 * 直接使用 new Date().toISOString() 会得到 UTC 日期，在东八区凌晨 0-8 点会显示为前一天。 */
export function todayLocal(): string {
  const d = new Date();
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}
