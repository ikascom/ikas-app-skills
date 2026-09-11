'use client';

export async function loadProducts(token: string) {
  const res = await fetch('https://api.myikas.com/api/v2/admin/graphql', {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ query: '{ listProduct { data { id } } }' }),
  });
  return res.json();
}
