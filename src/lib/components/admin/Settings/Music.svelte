<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config as backendConfig, user } from '$lib/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		getMusicGenerationModels,
		getConfig,
		updateConfig,
		verifyConfigUrl
	} from '$lib/apis/music';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	let loading = false;
	let models = null;
	let config = null;

	const getModels = async () => {
		models = await getMusicGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		if (config.MUSIC_GENERATION_ENGINE === 'mureka' && config.MUREKA_API_KEY === '') {
			toast.error($i18n.t('Mureka API Key is required.'));
			config.ENABLE_MUSIC_GENERATION = false;
			return null;
		}

		const res = await updateConfig(localStorage.token, { ...config }).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			if (res.ENABLE_MUSIC_GENERATION) {
				backendConfig.set(await getBackendConfig());
				getModels();
			}
			return res;
		}

		return null;
	};

	const saveHandler = async () => {
		loading = true;
		const res = await updateConfigHandler();
		if (res) {
			dispatch('save');
		}
		loading = false;
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;
			}

			if (config?.ENABLE_MUSIC_GENERATION) {
				getModels();
			}
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden pr-2">
		{#if config}
			<div>
				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Music Generation')}
								</div>
							</div>

							<Switch bind:state={config.ENABLE_MUSIC_GENERATION} />
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Create Music')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Music Generation Engine')}
								</div>
							</div>

							<select
								class="w-fit pr-8 cursor-pointer rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={config.MUSIC_GENERATION_ENGINE}
								placeholder={$i18n.t('Select Engine')}
							>
								<option value="mureka">{$i18n.t('Mureka')}</option>
							</select>
						</div>
					</div>

					{#if config.ENABLE_MUSIC_GENERATION}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="shrink-0">
										{$i18n.t('Model')}
									</div>
								</div>

								<Tooltip content={$i18n.t('Enter Model ID')} placement="top-start">
									<input
										list="music-model-list"
										class=" text-right text-sm bg-transparent outline-hidden max-w-full w-52"
										bind:value={config.MUSIC_GENERATION_MODEL}
										placeholder={$i18n.t('Select a model')}
										required
									/>

									<datalist id="music-model-list">
										{#each models ?? [] as model}
											<option value={model.id}>{model.name}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>
					{/if}

					{#if config?.MUSIC_GENERATION_ENGINE === 'mureka'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Mureka API Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Base URL')}
											bind:value={config.MUREKA_API_BASE_URL}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Mureka API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('API Key')}
											bind:value={config.MUREKA_API_KEY}
											required={false}
										/>
									</div>
									<button
										class="  transition"
										type="button"
										aria-label="verify connection"
										on:click={async () => {
											await updateConfigHandler();
											const res = await verifyConfigUrl(localStorage.token).catch((error) => {
												toast.error(`${error}`);
												return null;
											});

											if (res) {
												toast.success($i18n.t('Server connection verified'));
											}
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Get your API key from')}
								<a class=" text-gray-300 font-medium" href="https://platform.mureka.ai" target="_blank">
									platform.mureka.ai
								</a>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {loading
				? ' cursor-not-allowed'
				: ''}"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Save')}

			{#if loading}
				<span class="shrink-0">
					<Spinner />
				</span>
			{/if}
		</button>
	</div>
</form>
