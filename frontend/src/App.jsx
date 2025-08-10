import React, { useEffect, useMemo, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App(){
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState('')
  const [form, setForm] = useState({
    platform:'', username:'', email:'', password:'', phone:'', note:'', two_factor_enabled:false, tags:''
  })

  async function fetchList(){
    setLoading(true)
    const res = await fetch(`${API}/accounts`)
    const data = await res.json()
    setList(data)
    setLoading(false)
  }

  async function search(){
    if(!q){ return fetchList() }
    setLoading(true)
    const res = await fetch(`${API}/accounts/search?q=`+encodeURIComponent(q))
    const data = await res.json()
    setList(data)
    setLoading(false)
  }

  async function createItem(){
    const res = await fetch(`${API}/accounts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(form)})
    if(res.ok){
      setForm({platform:'', username:'', email:'', password:'', phone:'', note:'', two_factor_enabled:false, tags:''})
      fetchList()
      alert('Đã lưu & backup vào Google Sheets (nếu cấu hình).')
    }else{
      alert('Lỗi lưu dữ liệu')
    }
  }

  async function remove(id){
    if(!confirm('Xoá mục này?')) return
    const res = await fetch(`${API}/accounts/`+id,{method:'DELETE'})
    if(res.ok){ fetchList() }
  }

  useEffect(()=>{ fetchList() },[])

  const count = useMemo(()=> list.length, [list])

  return (
    <div>
      <h1>Account Manager</h1>

      <div className="card">
        <h3>Thêm nhanh</h3>
        <div className="row">
          <input placeholder="Nền tảng (platform)" value={form.platform} onChange={e=>setForm({...form, platform:e.target.value})} />
          <input placeholder="Username" value={form.username} onChange={e=>setForm({...form, username:e.target.value})} />
          <input placeholder="Email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} />
          <input placeholder="Password (demo)" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} />
          <input placeholder="Phone" value={form.phone} onChange={e=>setForm({...form, phone:e.target.value})} />
          <input placeholder="Tags (phân loại)" value={form.tags} onChange={e=>setForm({...form, tags:e.target.value})} />
          <label><input type="checkbox" checked={form.two_factor_enabled} onChange={e=>setForm({...form, two_factor_enabled:e.target.checked})} /> 2FA</label>
        </div>
        <textarea placeholder="Ghi chú" value={form.note} onChange={e=>setForm({...form, note:e.target.value})}></textarea>
        <div>
          <button onClick={createItem}>Lưu</button>
        </div>
      </div>

      <div className="card">
        <h3>Tìm kiếm nhanh</h3>
        <input placeholder="Từ khoá platform/username/email/tags" value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={search}>Tìm</button>
        <button onClick={fetchList}>Reset</button>
      </div>

      <div style={{marginTop:12}}>
        <b>Tổng số: {count}</b> {loading && <span>Đang tải...</span>}
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Platform</th><th>Username</th><th>Email</th><th>Tags</th><th>2FA</th><th>Cập nhật</th><th>Hành động</th>
            </tr>
          </thead>
          <tbody>
            {list.map(it=> (
              <tr key={it.id}>
                <td>{it.id}</td>
                <td>{it.platform}</td>
                <td>{it.username}</td>
                <td>{it.email}</td>
                <td>{it.tags}</td>
                <td>{it.two_factor_enabled? 'Yes':'No'}</td>
                <td>{new Date(it.updated_at).toLocaleString()}</td>
                <td><button onClick={()=>remove(it.id)}>Xoá</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

