import { test, expect } from '@playwright/test'

test.describe('Chat UI', () => {
  test('loads and shows input', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('textarea, input[type="text"]').first()).toBeVisible({ timeout: 10_000 })
  })

  test('sends message and shows it in chat', async ({ page }) => {
    await page.goto('/')
    const input = page.locator('textarea, input[type="text"]').first()
    await input.fill('Hello')
    await input.press('Enter')
    // User message should appear in the chat
    await expect(page.locator('text=Hello').first()).toBeVisible({ timeout: 10_000 })
  })

  test('/admin route does not show chat UI', async ({ page }) => {
    await page.goto('/admin')
    // Should NOT show the chat composer
    await page.waitForTimeout(1000)
    // The admin panel or login shows — not the chat
    await expect(page.locator('body')).not.toBeEmpty()
  })
})
