<script>
    import { authApi } from '$lib/api.js';
    import { authStore, notifications } from '$lib/stores.js';
    import { goto } from '$app/navigation';

    let full_name = '';
    let email = '';
    let password = '';
    let phone = '';
    let loading = false;
    let error = '';

    async function handleRegister() {
        loading = true;
        error = '';
        try {
            const res = await authApi.register({ full_name, email, password, phone });
            authStore.login(res.token, res.user);
            notifications.add('Registration successful!', 'success');
            goto('/dashboard');
        } catch (err) {
            error = err.message || 'Registration failed';
            notifications.add(error, 'error');
        } finally {
            loading = false;
        }
    }
</script>

<div class="flex items-center justify-center min-h-[80vh]">
    <div class="card w-full max-w-md mx-4">
        <div class="text-center mb-6">
            <span class="text-4xl">🚲</span>
            <h1 class="text-2xl font-bold text-gray-800 mt-2">Create Account</h1>
            <p class="text-gray-500">Join VeloTrack</p>
        </div>

        {#if error}
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">{error}</div>
        {/if}

        <form on:submit|preventDefault={handleRegister} class="space-y-4">
            <div>
                <label for="full_name" class="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input id="full_name" type="text" bind:value={full_name} class="input" placeholder="John Doe" required />
            </div>
            <div>
                <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input id="email" type="email" bind:value={email} class="input" placeholder="you@example.com" required />
            </div>
            <div>
                <label for="phone" class="block text-sm font-medium text-gray-700 mb-1">Phone (optional)</label>
                <input id="phone" type="tel" bind:value={phone} class="input" placeholder="+1234567890" />
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input id="password" type="password" bind:value={password} class="input" placeholder="••••••••" required minlength="6" />
            </div>
            <button type="submit" class="btn btn-primary w-full" disabled={loading}>
                {loading ? 'Creating account...' : 'Register'}
            </button>
        </form>

        <p class="text-center text-sm text-gray-500 mt-4">
            Already have an account? <a href="/login" class="text-primary-600 hover:underline">Login</a>
        </p>
    </div>
</div>

