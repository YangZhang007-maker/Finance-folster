import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables. Check your .env file.')
}

export const supabase = createClient(supabaseUrl || '', supabaseKey || '')

export async function searchCompanies(query) {
  const { data, error } = await supabase
    .from('companies')
    .select('*')
    .or(`name.ilike.%${query}%,code.ilike.%${query}%`)
    .limit(20)
  if (error) throw error
  return data
}

export async function getWatchlist() {
  const { data, error } = await supabase
    .from('watchlist')
    .select('code, companies(name)')
    .order('added_at', { ascending: false })
  if (error) throw error
  return data
}

export async function addToWatchlist(code) {
  const { error } = await supabase
    .from('watchlist')
    .upsert({ code }, { onConflict: 'code' })
  if (error) throw error
}

export async function removeFromWatchlist(code) {
  const { error } = await supabase
    .from('watchlist')
    .delete()
    .eq('code', code)
  if (error) throw error
}

export async function getFinancialIndicators(codes) {
  const { data, error } = await supabase
    .from('financial_indicators')
    .select('*')
    .in('code', codes)
    .order('report_date', { ascending: false })
  if (error) throw error

  const seen = new Set()
  const latest = []
  for (const row of data || []) {
    if (!seen.has(row.code)) {
      seen.add(row.code)
      latest.push(row)
    }
  }
  return latest
}

export async function getCompanyNames(codes) {
  const { data, error } = await supabase
    .from('companies')
    .select('code, name')
    .in('code', codes)
  if (error) throw error
  const map = {}
  for (const c of data || []) {
    map[c.code] = c.name
  }
  return map
}

export async function getAnnualFinancials(code) {
  const { data, error } = await supabase
    .from('annual_financials')
    .select('*')
    .eq('code', code)
    .order('report_date', { ascending: true })
  if (error) throw error
  return data || []
}

export async function getAnnualFinancialsV2(code) {
  const { data, error } = await supabase
    .from('annual_financials_v2')
    .select('*')
    .eq('code', code)
    .order('year', { ascending: true })
  if (error) throw error
  return data || []
}

export async function searchAllCompanies(query) {
  const { data, error } = await supabase
    .from('companies')
    .select('code, name')
    .or(`name.ilike.%${query}%,code.ilike.%${query}%`)
    .limit(50)
  if (error) throw error
  return data || []
}

/** 获取公司列表（含 sector），按 codes 筛选 */
export async function getCompaniesByCodes(codes) {
  if (!codes || codes.length === 0) return []
  const all = []
  for (let i = 0; i < codes.length; i += 300) {
    const batch = codes.slice(i, i + 300)
    const { data, error } = await supabase
      .from('companies')
      .select('code, name, sector')
      .in('code', batch)
    if (error) throw error
    if (data) all.push(...data)
  }
  return all
}

/** 批量获取年度财务数据（指定年份），按 codes 筛选 */
export async function getFinancialsByYear(codes, year) {
  if (!codes || codes.length === 0) return []
  const all = []
  for (let i = 0; i < codes.length; i += 200) {
    const batch = codes.slice(i, i + 200)
    const { data, error } = await supabase
      .from('annual_financials_v2')
      .select('code, year, gross_profit, parent_net_profit, operating_revenue, total_assets, roe, gross_margin, net_profit_margin, selling_to_gross')
      .in('code', batch)
      .eq('year', year)
    if (error) throw error
    if (data) all.push(...data)
  }
  return all
}