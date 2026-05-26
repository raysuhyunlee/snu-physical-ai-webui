<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { user } from '$lib/stores';
	import { musicGenerations } from '$lib/apis/music';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let loading = false;

	let prompt = '';
	let lyrics = '';
	let generatedTracks: { url: string; duration?: number }[] = [];

	let promptTextareaElement: HTMLTextAreaElement;

	const resizePromptTextarea = () => {
		if (promptTextareaElement) {
			promptTextareaElement.style.height = '';
			promptTextareaElement.style.height = Math.min(promptTextareaElement.scrollHeight, 150) + 'px';
		}
	};

	const submitHandler = async () => {
		if (!prompt.trim()) {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}

		loading = true;
		try {
			const result = await musicGenerations(
				localStorage.token,
				prompt,
				lyrics.trim() ? lyrics : undefined
			);

			if (result) {
				generatedTracks = [...result, ...generatedTracks];
			}
		} catch (error) {
			console.error('Music generation error:', error);
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const downloadTrack = async (url: string, index: number) => {
		try {
			const response = await fetch(url);
			const blob = await response.blob();
			const blobUrl = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = blobUrl;
			a.download = `music-${Date.now()}-${index}.mp3`;
			a.click();
			URL.revokeObjectURL(blobUrl);
		} catch (error) {
			toast.error($i18n.t('Failed to download'));
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		loaded = true;
	});
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col h-full px-4">
			<!-- Results Area -->
			<div
				class=" pt-0.5 pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="music-container"
			>
				<div class=" h-full w-full flex flex-col">
					<div class="flex-1 p-1">
						{#if generatedTracks.length > 0}
							<div class="flex flex-col gap-3">
								{#each generatedTracks as track, index}
									<div
										class="flex items-center gap-3 p-3 rounded-lg border border-gray-100/30 dark:border-gray-850/30"
									>
										<audio controls src={track.url} class="w-full">
											<track kind="captions" />
										</audio>
										<button
											class="shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-white transition"
											aria-label={$i18n.t('Download')}
											on:click={() => downloadTrack(track.url, index)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="w-5 h-5"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
												<polyline points="7,10 12,15 17,10" />
												<line x1="12" y1="15" x2="12" y2="3" />
											</svg>
										</button>
									</div>
								{/each}
							</div>
						{:else}
							<div
								class="h-full flex items-center justify-center text-gray-400 dark:text-gray-600 text-sm"
							>
								{$i18n.t('Generated music will appear here')}
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Input Area -->
			<div class="pb-3">
				<div class="border border-gray-100/30 dark:border-gray-850/30 w-full px-3 py-2.5 rounded-xl">
					<!-- Prompt Textarea -->
					<div class="py-0.5">
						<textarea
							bind:this={promptTextareaElement}
							bind:value={prompt}
							class=" w-full h-full bg-transparent resize-none outline-hidden text-sm"
							placeholder={$i18n.t('Describe the music (e.g. r&b, slow, male vocal)...')}
							on:input={resizePromptTextarea}
							on:focus={resizePromptTextarea}
							on:keydown={(e) => {
								if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !loading) {
									e.preventDefault();
									submitHandler();
								}
							}}
							rows="2"
						/>
					</div>

					<!-- Lyrics Textarea -->
					<div class="py-0.5 mt-1 border-t border-gray-100/30 dark:border-gray-850/30">
						<textarea
							bind:value={lyrics}
							class=" w-full h-full bg-transparent resize-none outline-hidden text-sm"
							placeholder={$i18n.t('Lyrics (optional, leave empty for auto)...')}
							rows="3"
						/>
					</div>

					<!-- Actions -->
					<div class="flex justify-end items-center gap-2 mt-2">
						<div class="flex gap-2 shrink-0">
							{#if !loading}
								<button
									disabled={prompt.trim() === ''}
									class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
									on:click={submitHandler}
								>
									{$i18n.t('Run')}
								</button>
							{:else}
								<button
									class="px-3.5 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-lg flex items-center gap-2"
									disabled
								>
									<Spinner className="size-4" />
									{$i18n.t('Generating...')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
