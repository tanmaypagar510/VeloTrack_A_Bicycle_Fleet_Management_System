<script>
    import { authApi } from '$lib/api.js';
    import { authStore, notifications } from '$lib/stores.js';
    import { goto } from '$app/navigation';

    let email = '';
    let password = '';
    let loading = false;
    let error = '';

    async function handleLogin() {
        loading = true;
        error = '';
        try {
            const res = await authApi.login(email, password);
            authStore.login(res.token, res.user);
            notifications.add('Login successful!', 'success');
            goto('/dashboard');
        } catch (err) {
            error = err.message || 'Login failed';
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
            <h1 class="text-2xl font-bold text-gray-800 mt-2">Welcome Back</h1>
            <p class="text-gray-500">Sign in to VeloTrack</p>
        </div>

        {#if error}
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                {error}
            </div>
        {/if}

        <form on:submit|preventDefault={handleLogin} class="space-y-4">
            <div>
                <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                    id="email"
                    type="email"
                    bind:value={email}
                    class="input"
                    placeholder="you@example.com"
                    required
                />
            </div>

            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                    id="password"
                    type="password"
                    bind:value={password}
                    class="input"
                    placeholder="••••••••"
                    required
                />
            </div>

            <button type="submit" class="btn btn-primary w-full" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
            </button>
        </form>

        <p class="text-center text-sm text-gray-500 mt-4">
            Don't have an account? <a href="/register" class="text-primary-600 hover:underline">Register</a>
        </p>
    </div>
</div>

