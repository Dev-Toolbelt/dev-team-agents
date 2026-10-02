// @vitest-environment jsdom
/**
 * The account screens (ADR-0029). What must never happen here: the app usable while the
 * gate says it is not (in `enforce`), a flash of the app before the first answer, a secret
 * that outlives the call that carried it, a destructive action without its typed
 * confirmation, or a failure that shows the CLI's own text (which carries the address) or
 * reveals whether an address is registered.
 */
import './setup.js';
import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from '../../src/renderer/App.js';
import { AccountProvider } from '../../src/renderer/account/AccountContext.js';
import { AccountGate } from '../../src/renderer/account/AccountGate.js';
import { Profile } from '../../src/renderer/account/Profile.js';
import { SignIn } from '../../src/renderer/account/SignIn.js';
import { authProfile, authState, blockedState, deferred, fail, fakeBridge, installBridge, ok, signedOutState } from './support.js';
import type { AuthState, DevteamBridge } from '../../src/shared/api.js';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const GOOD_CODE = '12345678';

function mountGate(bridge: DevteamBridge, onOpenAccount = vi.fn()) {
  installBridge(bridge);
  render(
    <AccountProvider enabled>
      <AccountGate onOpenAccount={onOpenAccount}>
        <p>the app itself</p>
      </AccountGate>
    </AccountProvider>,
  );
  return { onOpenAccount };
}

const checkReturning = (state: AuthState) =>
  vi.fn(() => Promise.resolve(ok(state, { outcome: state.entitled ? 'success' : 'findings' })));

describe('the gate', () => {
  it('shows nothing of the app until the first answer', async () => {
    const pending = deferred<ReturnType<typeof ok<AuthState>>>();
    mountGate(fakeBridge({ authCheck: vi.fn(() => pending.promise) }));
    expect(screen.getByRole('status')).toHaveTextContent(/checking your account/i);
    expect(screen.queryByText('the app itself')).not.toBeInTheDocument();
    pending.resolve(ok(authState()));
    expect(await screen.findByText('the app itself')).toBeInTheDocument();
  });

  it('renders the app untouched for an entitled account', async () => {
    mountGate(fakeBridge());
    expect(await screen.findByText('the app itself')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('in enforce mode shows only the sign-in screen when signed out', async () => {
    mountGate(fakeBridge({ authCheck: checkReturning(signedOutState({ gate_mode: 'enforce' })) }));
    expect(await screen.findByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
    expect(screen.queryByText('the app itself')).not.toBeInTheDocument();
  });

  it.each([
    ['trial_expired', /your trial has ended/i],
    ['banned', /this account is blocked/i],
    ['needs_online_check', /connection is needed/i],
    ['invalid', /could not be verified/i],
  ] as const)('in enforce mode shows the blocked screen for %s', async (status, title) => {
    mountGate(fakeBridge({ authCheck: checkReturning(blockedState(status, { gate_mode: 'enforce' })) }));
    expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.queryByText('the app itself')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /check again/i })).toBeInTheDocument();
    expect(screen.getByText(/projects and files are untouched/i)).toBeInTheDocument();
  });

  it('check again asks the CLI again and lets the person in once it is entitled', async () => {
    const user = userEvent.setup();
    const authCheck = vi
      .fn()
      .mockResolvedValueOnce(ok(blockedState('needs_online_check', { gate_mode: 'enforce' }), { outcome: 'findings' }))
      .mockResolvedValue(ok(authState({ gate_mode: 'enforce' })));
    mountGate(fakeBridge({ authCheck }));
    await user.click(await screen.findByRole('button', { name: /check again/i }));
    expect(await screen.findByText('the app itself')).toBeInTheDocument();
    expect(authCheck).toHaveBeenCalledTimes(2);
  });

  it('signing out from the blocked screen goes through the CLI and re-checks', async () => {
    const user = userEvent.setup();
    const authCheck = vi
      .fn()
      .mockResolvedValueOnce(ok(blockedState('trial_expired', { gate_mode: 'enforce' }), { outcome: 'findings' }))
      .mockResolvedValue(ok(signedOutState({ gate_mode: 'enforce' }), { outcome: 'findings' }));
    const authLogout = vi.fn(() => Promise.resolve(ok({ signed_in: false, server_revoked: true })));
    mountGate(fakeBridge({ authCheck, authLogout }));
    await user.click(await screen.findByRole('button', { name: /sign out/i }));
    expect(authLogout).toHaveBeenCalledOnce();
    expect(await screen.findByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
  });

  it('in warn mode keeps the app and shows a banner that can be dismissed and opens the account', async () => {
    const user = userEvent.setup();
    const { onOpenAccount } = mountGate(fakeBridge({ authCheck: checkReturning(blockedState('trial_expired')) }));
    expect(await screen.findByText('the app itself')).toBeInTheDocument();
    const banner = screen.getByRole('alert');
    expect(banner).toHaveTextContent(/your trial has ended/i);
    await user.click(within(banner).getByRole('button', { name: /open account/i }));
    expect(onOpenAccount).toHaveBeenCalledOnce();
    await user.click(within(banner).getByRole('button', { name: /dismiss/i }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('the app itself')).toBeInTheDocument();
  });

  it('in warn mode a signed-out person is offered "Sign in"', async () => {
    mountGate(fakeBridge({ authCheck: checkReturning(signedOutState()) }));
    expect(await screen.findByRole('button', { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByText('the app itself')).toBeInTheDocument();
  });

  it('treats a failed check as unknown, never as entitled: banner in warn, blocked screen in enforce', async () => {
    mountGate(fakeBridge({ authCheck: vi.fn(() => Promise.resolve(fail('boom', { reason: 'not_configured' }))) }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be checked/i);
    cleanup();
    // `gate_mode` only arrives in a document, so an unknown account stays on the warn default.
    expect(screen.queryByText('boom')).not.toBeInTheDocument();
  });

  it('survives a rejected bridge call', async () => {
    mountGate(fakeBridge({ authCheck: vi.fn(() => Promise.reject(new Error('ipc down'))) }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be checked/i);
  });
});

describe('sign-in', () => {
  function mount(overrides: Partial<DevteamBridge> = {}) {
    const bridge = fakeBridge(overrides);
    installBridge(bridge);
    const onSignedIn = vi.fn();
    render(<SignIn onSignedIn={onSignedIn} />);
    return { bridge, onSignedIn, user: userEvent.setup() };
  }

  it.each([
    ['google', /continue with google/i],
    ['github', /continue with github/i],
  ] as const)('signs in with %s through the CLI and says the browser is waiting', async (provider, name) => {
    const pending = deferred<ReturnType<typeof ok<AuthState>>>();
    const { bridge, onSignedIn, user } = mount({ authLoginOAuth: vi.fn(() => pending.promise) });
    await user.click(screen.getByRole('button', { name }));
    expect(bridge.authLoginOAuth).toHaveBeenCalledWith(provider);
    expect(screen.getByRole('status')).toHaveTextContent(/finish signing in in your browser/i);
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeDisabled();
    pending.resolve(ok(authState()));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(authState()));
  });

  it('signs in with an emailed code in two steps', async () => {
    const { bridge, onSignedIn, user } = mount({
      authOtpStart: vi.fn(() => Promise.resolve(ok({ sent: true }))),
      authOtpVerify: vi.fn(() => Promise.resolve(ok(authState()))),
    });
    await user.type(screen.getByLabelText(/email address/i), '  Ana@Example.com ');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(bridge.authOtpStart).toHaveBeenCalledWith('ana@example.com', null);
    expect(await screen.findByText(/if ana@example.com can sign in/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^code/i), '1234 5678');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    expect(bridge.authOtpVerify).toHaveBeenCalledWith('ana@example.com', '1234 5678');
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledOnce());
  });

  it('validates on submit and sends nothing for a bad address or code', async () => {
    const { bridge, user } = mount();
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(screen.getByText(/this field is required/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/email address/i), 'nope');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(screen.getByText(/does not look like an email/i)).toBeInTheDocument();
    expect(bridge.authOtpStart).not.toHaveBeenCalled();
  });

  it('refuses a malformed code without calling verify and a wrong code shows a generic sentence', async () => {
    const { bridge, user } = mount({
      authOtpStart: vi.fn(() => Promise.resolve(ok({ sent: true }))),
      authOtpVerify: vi.fn(() => Promise.resolve(fail('invalid code for ana@example.com', { reason: 'invalid_code', exitCode: 1 }))),
    });
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    await user.type(await screen.findByLabelText(/^code/i), '123');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    expect(screen.getByText(/code is 8 digits/i)).toBeInTheDocument();
    expect(bridge.authOtpVerify).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText(/^code/i));
    await user.type(screen.getByLabelText(/^code/i), GOOD_CODE);
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('That code is not valid or has expired.');
    // The CLI's own sentence names the address; it is never shown.
    expect(screen.queryByText(/invalid code for ana@example.com/)).not.toBeInTheDocument();
  });

  it('signs in with email and password and shows a generic error for a wrong one', async () => {
    const authPasswordSignIn = vi
      .fn()
      .mockResolvedValueOnce(fail('invalid credentials', { reason: 'invalid_credentials' }))
      .mockResolvedValue(ok(authState()));
    const { onSignedIn, user } = mount({ authPasswordSignIn });
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'wrong-password');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The email or password is not correct.');
    await user.clear(screen.getByLabelText(/^password$/i));
    await user.type(screen.getByLabelText(/^password$/i), 'correct-horse-battery');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledOnce());
    expect(authPasswordSignIn).toHaveBeenLastCalledWith('ana@example.com', 'correct-horse-battery');
  });

  it('the password field can be revealed and hidden again', async () => {
    const { user } = mount();
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    const field = screen.getByLabelText(/^password$/i);
    expect(field).toHaveAttribute('type', 'password');
    await user.click(screen.getByRole('button', { name: /^show$/i }));
    expect(field).toHaveAttribute('type', 'text');
    await user.click(screen.getByRole('button', { name: /^hide$/i }));
    expect(field).toHaveAttribute('type', 'password');
  });

  it('creates an account: password policy, then the emailed code, and clears the password after start', async () => {
    const authPasswordSignUpStart = vi.fn(() => Promise.resolve(ok({ pending: true as const })));
    const authPasswordSignUpFinish = vi.fn(() => Promise.resolve(ok(authState())));
    const { onSignedIn, user } = mount({ authPasswordSignUpStart, authPasswordSignUpFinish });
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    await user.click(screen.getByRole('button', { name: /create an account/i }));
    await user.type(screen.getByLabelText(/name \(optional\)/i), 'Ana');
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.type(screen.getByLabelText(/choose a password/i), 'short');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(screen.getByText(/10 to 64 characters/i, { selector: '[role=alert]' })).toBeInTheDocument();
    expect(authPasswordSignUpStart).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText(/choose a password/i));
    await user.type(screen.getByLabelText(/choose a password/i), 'a-long-enough-password');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(authPasswordSignUpStart).toHaveBeenCalledWith('ana@example.com', 'a-long-enough-password', 'Ana');
    expect(await screen.findByRole('heading', { name: /confirm your email/i })).toBeInTheDocument();
    expect(screen.queryByDisplayValue('a-long-enough-password')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/^code/i), GOOD_CODE);
    await user.click(screen.getByRole('button', { name: /confirm and sign in/i }));
    expect(authPasswordSignUpFinish).toHaveBeenCalledWith(GOOD_CODE);
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledOnce());
  });

  it('cancelling a sign-up that is waiting for its code ends the held process', async () => {
    const authPasswordSignUpCancel = vi.fn(() => Promise.resolve());
    const { user } = mount({
      authPasswordSignUpStart: vi.fn(() => Promise.resolve(ok({ pending: true as const }))),
      authPasswordSignUpCancel,
    });
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    await user.click(screen.getByRole('button', { name: /create an account/i }));
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.type(screen.getByLabelText(/choose a password/i), 'a-long-enough-password');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await user.click(await screen.findByRole('button', { name: /^cancel$/i }));
    expect(authPasswordSignUpCancel).toHaveBeenCalledOnce();
    expect(screen.getByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
  });

  it('leaving the screen while a sign-up waits also ends it', async () => {
    const authPasswordSignUpCancel = vi.fn(() => Promise.resolve());
    const bridge = fakeBridge({
      authPasswordSignUpStart: vi.fn(() => Promise.resolve(ok({ pending: true as const }))),
      authPasswordSignUpCancel,
    });
    installBridge(bridge);
    const { unmount } = render(<SignIn onSignedIn={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    await user.click(screen.getByRole('button', { name: /create an account/i }));
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.type(screen.getByLabelText(/choose a password/i), 'a-long-enough-password');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await screen.findByRole('heading', { name: /confirm your email/i });
    unmount();
    expect(authPasswordSignUpCancel).toHaveBeenCalledOnce();
  });

  it('resets a forgotten password: send the code, then code and new password', async () => {
    const authPasswordResetStart = vi.fn(() => Promise.resolve(ok({ sent: true })));
    const authPasswordResetFinish = vi.fn(() => Promise.resolve(ok(authState())));
    const { onSignedIn, user } = mount({ authPasswordResetStart, authPasswordResetFinish });
    await user.click(screen.getByRole('tab', { name: /email and password/i }));
    await user.click(screen.getByRole('button', { name: /forgot your password/i }));
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.click(screen.getByRole('button', { name: /send the code/i }));
    expect(authPasswordResetStart).toHaveBeenCalledWith('ana@example.com');
    await user.type(await screen.findByLabelText(/^code/i), GOOD_CODE);
    await user.type(screen.getByLabelText(/new password/i), 'short');
    await user.click(screen.getByRole('button', { name: /set the new password/i }));
    expect(authPasswordResetFinish).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText(/new password/i));
    await user.type(screen.getByLabelText(/new password/i), 'a-brand-new-password');
    await user.click(screen.getByRole('button', { name: /set the new password/i }));
    expect(authPasswordResetFinish).toHaveBeenCalledWith('ana@example.com', GOOD_CODE, 'a-brand-new-password');
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledOnce());
  });

  it('answers the same whether or not an address is known: the sent step does not depend on the address', async () => {
    // The CLI answers `sent: true` for any address (SR-10); the screen must not vary either.
    const { user } = mount({ authOtpStart: vi.fn(() => Promise.resolve(ok({ sent: true }))) });
    await user.type(screen.getByLabelText(/email address/i), 'nobody@example.com');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(await screen.findByText(/if nobody@example.com can sign in/i)).toBeInTheDocument();
  });

  it('maps rate limiting and an unreachable server to their own generic sentences', async () => {
    const { user } = mount({
      authOtpStart: vi
        .fn()
        .mockResolvedValueOnce(fail('too many requests; try again in 30 seconds', { reason: 'rate_limited', exitCode: 3 }))
        .mockResolvedValueOnce(fail('x', { reason: 'unreachable', exitCode: 3 }))
        .mockResolvedValueOnce(fail('weird', { kind: 'contract-breach', exitCode: null })),
    });
    await user.type(screen.getByLabelText(/email address/i), 'ana@example.com');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/too many attempts/i);
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/could not be reached/i));
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Try again.'));
    expect(screen.queryByText('weird')).not.toBeInTheDocument();
  });

  it('speaks Portuguese when the OS language is pt-BR', () => {
    vi.spyOn(window.navigator, 'language', 'get').mockReturnValue('pt-BR');
    mount();
    expect(screen.getByRole('heading', { name: /entre no dev-team-agents/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continuar com o google/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /código por e-mail/i })).toBeInTheDocument();
  });
});

describe('profile', () => {
  async function mount(overrides: Partial<DevteamBridge> = {}, state: AuthState = authState()) {
    const bridge = fakeBridge({ authCheck: checkReturning(state), ...overrides });
    installBridge(bridge);
    render(
      <AccountProvider enabled>
        <Profile />
      </AccountProvider>,
    );
    await screen.findByLabelText(/display name/i);
    return { bridge, user: userEvent.setup() };
  }

  it('shows the person, their initials, the licence and their sign-in methods', async () => {
    await mount();
    expect(screen.getByRole('heading', { level: 2, name: 'Ana Souza' })).toBeInTheDocument();
    expect(screen.getByText('AS')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /unlink google/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /link github/i })).toBeInTheDocument();
  });

  it('shows a trial with its end date', async () => {
    await mount(
      {},
      authState({ entitlement: { status: 'trial', reason: null, features: [], trial_ends_at: 1_900_000_000, expires_at: null } }),
    );
    expect(screen.getByText('Trial')).toBeInTheDocument();
    expect(screen.getByText(/trial ends/i)).toBeInTheDocument();
  });

  it('warns when the machine keeps the session in a plain file', async () => {
    await mount({}, authState({ secret_backend_insecure: true }));
    expect(screen.getByRole('alert')).toHaveTextContent(/plain file/i);
  });

  it('updates the display name, validating first', async () => {
    const authProfileUpdate = vi.fn((name: string) => Promise.resolve(ok({ display_name: name })));
    const { user } = await mount({ authProfileUpdate });
    const field = screen.getByLabelText(/display name/i);
    await user.clear(field);
    await user.click(screen.getByRole('button', { name: /save name/i }));
    expect(screen.getByText(/this field is required/i)).toBeInTheDocument();
    expect(authProfileUpdate).not.toHaveBeenCalled();
    await user.type(field, 'Ana S.');
    await user.click(screen.getByRole('button', { name: /save name/i }));
    expect(authProfileUpdate).toHaveBeenCalledWith('Ana S.');
    expect(await screen.findByText('Name saved.')).toBeInTheDocument();
  });

  it('changes the email in two steps with both codes', async () => {
    const authEmailChangeStart = vi.fn(() => Promise.resolve(ok({ sent: true })));
    const authEmailChangeConfirm = vi.fn(() => Promise.resolve(ok({ confirmed: true, email: 'new@example.com' })));
    const { user } = await mount({ authEmailChangeStart, authEmailChangeConfirm });
    await user.click(screen.getByRole('button', { name: /change email/i }));
    await user.type(screen.getByLabelText(/new email address/i), 'New@Example.com');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    expect(authEmailChangeStart).toHaveBeenCalledWith('new@example.com');
    await user.type(await screen.findByLabelText(/code sent to the new address/i), GOOD_CODE);
    await user.click(screen.getByRole('button', { name: /confirm the change/i }));
    expect(authEmailChangeConfirm).toHaveBeenCalledWith('new@example.com', GOOD_CODE, null);
    expect(await screen.findByText('Email changed.')).toBeInTheDocument();
  });

  it('says it is waiting when only one of two addresses has confirmed', async () => {
    const { user } = await mount({
      authEmailChangeStart: vi.fn(() => Promise.resolve(ok({ sent: true }))),
      authEmailChangeConfirm: vi.fn(() => Promise.resolve(ok({ confirmed: false, email: 'ana.souza@example.com' }))),
    });
    await user.click(screen.getByRole('button', { name: /change email/i }));
    await user.type(screen.getByLabelText(/new email address/i), 'new@example.com');
    await user.click(screen.getByRole('button', { name: /send me a code/i }));
    await user.type(await screen.findByLabelText(/code sent to the new address/i), GOOD_CODE);
    await user.click(screen.getByRole('button', { name: /confirm the change/i }));
    expect(await screen.findByText(/waiting for the other address/i)).toBeInTheDocument();
  });

  it('links and unlinks providers, and reloads the profile afterwards', async () => {
    const authIdentityLink = vi.fn(() => Promise.resolve(ok({ linked: 'github', identities: [] })));
    const authIdentityUnlink = vi.fn(() => Promise.resolve(ok({ unlinked: 'google' })));
    const { bridge, user } = await mount({ authIdentityLink, authIdentityUnlink });
    await user.click(screen.getByRole('button', { name: /link github/i }));
    expect(authIdentityLink).toHaveBeenCalledWith('github');
    expect(await screen.findByText('GitHub linked.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /unlink google/i }));
    expect(authIdentityUnlink).toHaveBeenCalledWith('google');
    await waitFor(() => expect(vi.mocked(bridge.authProfileGet).mock.calls.length).toBeGreaterThanOrEqual(3));
  });

  it('will not offer to unlink the only sign-in method', async () => {
    await mount({
      authProfileGet: vi.fn(() => Promise.resolve(ok(authProfile({ identities: [{ id: 'g', provider: 'google', email: 'a@b.co' }] })))),
    });
    expect(screen.getByRole('button', { name: /unlink google/i })).toBeDisabled();
  });

  it('explains a refused unlink in generic words', async () => {
    const { user } = await mount({
      authIdentityUnlink: vi.fn(() => Promise.resolve(fail('only way to sign in', { reason: 'last_identity', exitCode: 1 }))),
    });
    await user.click(screen.getByRole('button', { name: /unlink google/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/only way to sign in, so it cannot be removed/i);
  });

  it('changes the password: policy, both values sent, and the fields are gone afterwards', async () => {
    const authPasswordChange = vi.fn(() => Promise.resolve(ok({ changed: true as const, other_sessions_revoked: true })));
    const { user } = await mount({ authPasswordChange });
    await user.click(screen.getByRole('button', { name: /^change password$/i }));
    await user.type(screen.getByLabelText(/current password/i), 'old-password-1');
    await user.type(screen.getByLabelText(/^new password$/i), 'short');
    await user.click(screen.getByRole('button', { name: /^change password$/i }));
    expect(authPasswordChange).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText(/^new password$/i));
    await user.type(screen.getByLabelText(/^new password$/i), 'new-password-123');
    await user.click(screen.getByRole('button', { name: /^change password$/i }));
    expect(authPasswordChange).toHaveBeenCalledWith('old-password-1', 'new-password-123');
    expect(await screen.findByText(/other devices were signed out/i)).toBeInTheDocument();
    expect(screen.queryByDisplayValue('new-password-123')).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('old-password-1')).not.toBeInTheDocument();
  });

  it('a wrong current password reports one generic failure and clears both fields without nagging', async () => {
    const { user } = await mount({
      authPasswordChange: vi.fn(() => Promise.resolve(fail('invalid credentials', { reason: 'invalid_credentials', exitCode: 1 }))),
    });
    await user.click(screen.getByRole('button', { name: /^change password$/i }));
    await user.type(screen.getByLabelText(/current password/i), 'wrong-password-1');
    await user.type(screen.getByLabelText(/^new password$/i), 'new-password-123');
    await user.click(screen.getByRole('button', { name: /^change password$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The email or password is not correct.');
    expect(screen.getByLabelText(/current password/i)).toHaveValue('');
    expect(screen.getAllByRole('alert')).toHaveLength(1);
  });

  it('omits the password section for an account with no password sign-in', async () => {
    await mount({
      authProfileGet: vi.fn(() => Promise.resolve(ok(authProfile({ identities: [{ id: 'g', provider: 'google', email: null }] })))),
    });
    expect(screen.queryByRole('heading', { name: /^password$/i })).not.toBeInTheDocument();
  });

  it('signs out through the CLI and falls back to the sign-in screen', async () => {
    const authCheck = vi
      .fn()
      .mockResolvedValueOnce(ok(authState()))
      .mockResolvedValue(ok(signedOutState(), { outcome: 'findings' }));
    const authLogout = vi.fn(() => Promise.resolve(ok({ signed_in: false, server_revoked: true })));
    const { user } = await mount({ authCheck, authLogout });
    await user.click(screen.getAllByRole('button', { name: /^sign out$/i })[0]!);
    expect(authLogout).toHaveBeenCalledOnce();
    expect(await screen.findByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
  });

  describe('delete account', () => {
    it('sends nothing until the confirmation word is typed, then needs the emailed code', async () => {
      const authDeleteStart = vi.fn(() => Promise.resolve(ok({ sent: true })));
      const authDeleteConfirm = vi.fn(() => Promise.resolve(ok({ deleted: true as const })));
      const authCheck = vi
        .fn()
        .mockResolvedValueOnce(ok(authState()))
        .mockResolvedValue(ok(signedOutState(), { outcome: 'findings' }));
      const { user } = await mount({ authDeleteStart, authDeleteConfirm, authCheck });
      await user.click(screen.getByRole('button', { name: /delete my account/i }));
      const send = screen.getByRole('button', { name: /send a confirmation code/i });
      expect(send).toBeDisabled();
      await user.type(screen.getByLabelText(/type delete to confirm/i), 'delet');
      expect(send).toBeDisabled();
      await user.type(screen.getByLabelText(/type delete to confirm/i), 'e');
      expect(send).toBeEnabled();
      await user.click(send);
      expect(authDeleteStart).toHaveBeenCalledOnce();
      expect(authDeleteConfirm).not.toHaveBeenCalled();
      await user.type(await screen.findByLabelText(/confirmation code/i), GOOD_CODE);
      await user.click(screen.getByRole('button', { name: /delete account permanently/i }));
      expect(authDeleteConfirm).toHaveBeenCalledWith(GOOD_CODE);
      expect(await screen.findByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
    });

    it('can be cancelled before anything is sent', async () => {
      const authDeleteStart = vi.fn();
      const { user } = await mount({ authDeleteStart });
      await user.click(screen.getByRole('button', { name: /delete my account/i }));
      await user.click(screen.getByRole('button', { name: /^cancel$/i }));
      expect(authDeleteStart).not.toHaveBeenCalled();
      expect(screen.getByRole('button', { name: /delete my account/i })).toBeInTheDocument();
    });

    it('a wrong code reports a generic failure and deletes nothing', async () => {
      const { user } = await mount({
        authDeleteStart: vi.fn(() => Promise.resolve(ok({ sent: true }))),
        authDeleteConfirm: vi.fn(() => Promise.resolve(fail('bad', { reason: 'invalid_code', exitCode: 1 }))),
      });
      await user.click(screen.getByRole('button', { name: /delete my account/i }));
      await user.type(screen.getByLabelText(/type delete to confirm/i), 'DELETE');
      await user.click(screen.getByRole('button', { name: /send a confirmation code/i }));
      await user.type(await screen.findByLabelText(/confirmation code/i), GOOD_CODE);
      await user.click(screen.getByRole('button', { name: /delete account permanently/i }));
      expect(await screen.findByRole('alert')).toHaveTextContent('That code is not valid or has expired.');
      expect(screen.getByRole('heading', { level: 2, name: 'Ana Souza' })).toBeInTheDocument();
    });
  });
});

describe('the shell', () => {
  it('shows the initials in the header, opens the Account tab from them, and gates the tabs', async () => {
    installBridge(fakeBridge());
    const user = userEvent.setup();
    render(<App />);
    const avatar = await screen.findByRole('button', { name: /account: ana souza/i });
    expect(avatar).toHaveTextContent('AS');
    await user.click(avatar);
    expect(await screen.findByRole('heading', { level: 2, name: 'Ana Souza' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Account', selected: true })).toBeInTheDocument();
  });

  it('shows only the sign-in screen, no tabs, when the gate enforces and the account is signed out', async () => {
    installBridge(fakeBridge({ authCheck: checkReturning(signedOutState({ gate_mode: 'enforce' })) }));
    render(<App />);
    expect(await screen.findByRole('heading', { name: /sign in to dev-team-agents/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Projects' })).not.toBeInTheDocument();
  });

  it('asks the CLI nothing about the account while no CLI was found', async () => {
    const authCheck = vi.fn(() => Promise.resolve(ok(authState())));
    installBridge(fakeBridge({ authCheck, resolveCli: vi.fn(() => Promise.resolve({ found: false as const, rejected: [], searchedCount: 0, searchedBySource: [], remedy: [] })) }));
    render(<App />);
    await screen.findByText(/no devteam cli on this host/i);
    expect(authCheck).not.toHaveBeenCalled();
  });
});
