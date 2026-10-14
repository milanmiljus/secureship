import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:8000'

// Detect if Auth0 is enabled in the running stack.
// When AUTH0_DOMAIN is set, admin endpoints require a bearer token.
// The CRUD tests are skipped in that mode — they are designed for dev mode only.
async function isDevMode(request: Parameters<Parameters<typeof test>[1]>[0]['request']): Promise<boolean> {
  const res = await request.get(`${BASE}/admin/customers`)
  return res.status() !== 401
}

test.describe('Admin CRUD — dev mode', () => {
  test('can list customers', async ({ request }) => {
    const devMode = await isDevMode(request)
    if (!devMode) {
      test.skip()
      return
    }
    const res = await request.get(`${BASE}/admin/customers`)
    expect(res.ok()).toBeTruthy()
    const customers = await res.json()
    expect(Array.isArray(customers)).toBeTruthy()
    expect(customers.length).toBeGreaterThan(0)
  })

  test('can create and delete a customer', async ({ request }) => {
    const devMode = await isDevMode(request)
    if (!devMode) {
      test.skip()
      return
    }
    const create = await request.post(`${BASE}/admin/customers`, {
      data: {
        first_name: 'E2E',
        last_name: 'Test',
        phone_number: '+15550000001',
        address: '1 Test Street, Testville, TX 00001',
      },
    })
    expect(create.status()).toBe(201)
    const customer = await create.json()
    expect(customer.id).toBeTruthy()

    // Delete
    const del = await request.delete(`${BASE}/admin/customers/${customer.id}`)
    expect(del.status()).toBe(204)

    // Verify gone
    const get = await request.get(`${BASE}/admin/customers/${customer.id}`)
    expect(get.status()).toBe(404)
  })

  test('can create a shipment for a customer', async ({ request }) => {
    const devMode = await isDevMode(request)
    if (!devMode) {
      test.skip()
      return
    }
    // Create customer first
    const cust = await request.post(`${BASE}/admin/customers`, {
      data: { first_name: 'Ship', last_name: 'Test', phone_number: '+15550000002', address: '2 Ship Lane, Portland, OR 97201' },
    })
    const { id: customer_id } = await cust.json()

    const ship = await request.post(`${BASE}/admin/shipments`, {
      data: {
        customer_id,
        tracking_number: 'E2E-TRK-001',
        status: 'in_transit',
        carrier: 'FedEx',
        origin: 'Portland, OR',
        destination: 'Seattle, WA',
        estimated_delivery: '2026-12-01',
      },
    })
    expect(ship.status()).toBe(201)
    const shipment = await ship.json()
    expect(shipment.tracking_number).toBe('E2E-TRK-001')

    // Cleanup
    await request.delete(`${BASE}/admin/customers/${customer_id}`)
  })

  test('admin panel renders at /admin', async ({ page }) => {
    await page.goto('/admin')
    // Should show either the login card (with Auth0) or the admin panel (dev mode)
    await expect(page.locator('body')).not.toBeEmpty()
    // In dev mode: should show Customers tab
    const hasPanel = await page.locator('text=Customers').isVisible().catch(() => false)
    const hasLogin = await page.locator('text=Sign in').isVisible().catch(() => false)
    expect(hasPanel || hasLogin).toBeTruthy()
  })
})
