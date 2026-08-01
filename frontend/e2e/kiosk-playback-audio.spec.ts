import { expect, test } from '@playwright/test';

import { installYoutubeApiStub } from './fixtures/youtube-api-stub';

const API_URL = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000/api';
const OPERATOR_USERNAME = process.env.E2E_OPERATOR_USERNAME ?? 'op';
const OPERATOR_PASSWORD = process.env.E2E_OPERATOR_PASSWORD ?? 'change-me-please-1234';
const SAMPLE_VIDEO_ID = 'dQw4w9WgXcQ';

test.describe('kiosk playback audio (full stack)', () => {
  test('display reports sound and admin shows Sonando con audio', async ({ browser, request }) => {
    const login = await request.post(`${API_URL}/auth/login`, {
      data: { username: OPERATOR_USERNAME, password: OPERATOR_PASSWORD },
    });
    expect(login.ok()).toBeTruthy();

    const tokenResponse = await request.post(`${API_URL}/tokens`, {
      data: { label: 'e2e-playwright' },
    });
    expect(tokenResponse.ok()).toBeTruthy();
    const embedToken = (await tokenResponse.json()).token.token as string;

    const submit = await request.post(`${API_URL}/queue/dev-submit`, {
      data: { youtube_url_or_id: SAMPLE_VIDEO_ID },
    });
    expect(submit.ok()).toBeTruthy();

    const pending = await request.get(`${API_URL}/queue/pending`);
    expect(pending.ok()).toBeTruthy();
    const entryId = (await pending.json()).entries[0].id as string;

    const approve = await request.post(`${API_URL}/queue/${entryId}/approve`);
    expect(approve.ok()).toBeTruthy();

    const stateAfterApprove = await request.get(`${API_URL}/state`);
    expect(stateAfterApprove.ok()).toBeTruthy();
    expect((await stateAfterApprove.json()).now_playing).not.toBeNull();

    const kioskContext = await browser.newContext();
    const kioskPage = await kioskContext.newPage();
    await installYoutubeApiStub(kioskPage);
    await kioskPage.goto(`/?token=${encodeURIComponent(embedToken)}`);

    await expect(kioskPage.getByRole('button', { name: 'Activar sonido' })).not.toBeVisible({
      timeout: 20_000,
    });

    await expect
      .poll(async () => {
        const status = await request.get(`${API_URL}/display/playback-status`);
        if (!status.ok()) {
          return 'unavailable';
        }
        return (await status.json()).audio_mode as string;
      }, { timeout: 20_000 })
      .toBe('sound');

    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await adminPage.goto('/login');
    await adminPage.locator('input[name="username"]').fill(OPERATOR_USERNAME);
    await adminPage.locator('input[name="password"]').fill(OPERATOR_PASSWORD);
    await adminPage.getByRole('button', { name: 'Entrar' }).click();
    await adminPage.waitForURL('**/admin');

    await expect(adminPage.getByText(/Sonando con audio:/)).toBeVisible({ timeout: 20_000 });

    await kioskContext.close();
    await adminContext.close();
  });
});
