<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getCourses,
		getCourseById,
		createNewCourse,
		deleteCourseById,
		addFileToCourseById,
		removeFileFromCourseById
	} from '$lib/apis/courses';
	import { uploadFile } from '$lib/apis/files';
	import { courses as coursesStore } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let courses = [];

	let selectedCourse = null; // detailed course (with files)
	let uploading = false;

	// create form
	let showCreate = false;
	let newName = '';

	let fileInputElement;

	const loadCourses = async () => {
		const res = await getCourses(localStorage.token).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		courses = (res?.items ?? []).sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
		coursesStore.set(courses);
	};

	const selectCourse = async (id) => {
		selectedCourse = await getCourseById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
	};

	const createHandler = async () => {
		if (!newName.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}
		const res = await createNewCourse(localStorage.token, newName.trim()).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Course created'));
			showCreate = false;
			newName = '';
			await loadCourses();
			await selectCourse(res.id);
		}
	};

	const deleteHandler = async (id) => {
		const res = await deleteCourseById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Course deleted'));
			if (selectedCourse?.id === id) selectedCourse = null;
			await loadCourses();
		}
	};

	const uploadHandler = async (event) => {
		const file = event.target.files?.[0];
		if (!file || !selectedCourse) return;

		uploading = true;
		try {
			const uploaded = await uploadFile(localStorage.token, file);
			if (!uploaded?.id) throw $i18n.t('Upload failed');
			await addFileToCourseById(localStorage.token, selectedCourse.id, uploaded.id);
			toast.success($i18n.t('Material uploaded'));
			await selectCourse(selectedCourse.id);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			uploading = false;
			if (fileInputElement) fileInputElement.value = '';
		}
	};

	const removeFileHandler = async (fileId) => {
		const res = await removeFileFromCourseById(localStorage.token, selectedCourse.id, fileId).catch(
			(e) => {
				toast.error(`${e}`);
				return null;
			}
		);
		if (res) {
			toast.success($i18n.t('Material removed'));
			await selectCourse(selectedCourse.id);
		}
	};

	onMount(async () => {
		await loadCourses();
		loaded = true;
	});
</script>

{#if loaded}
	<div class="flex flex-col md:flex-row gap-4 px-4 md:px-8 py-2 h-full">
		<!-- Course list -->
		<div class="md:w-1/3 w-full flex flex-col gap-2">
			<div class="flex items-center justify-between">
				<div class="text-lg font-medium">{$i18n.t('Courses')}</div>
				<button
					class="px-2.5 py-1 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => (showCreate = !showCreate)}
				>
					{$i18n.t('New Course')}
				</button>
			</div>

			{#if showCreate}
				<div class="flex flex-col gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
					<input
						class="px-3 py-1.5 text-sm rounded-lg bg-white dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('Course name')}
						bind:value={newName}
					/>
					<div class="flex justify-end gap-2">
						<button
							class="px-2.5 py-1 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => (showCreate = false)}>{$i18n.t('Cancel')}</button
						>
						<button
							class="px-2.5 py-1 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black transition"
							on:click={createHandler}>{$i18n.t('Create')}</button
						>
					</div>
				</div>
			{/if}

			<div class="flex flex-col gap-1 overflow-y-auto">
				{#each courses as course (course.id)}
					<button
						class="flex flex-col text-left px-3 py-2 rounded-lg transition {selectedCourse?.id ===
						course.id
							? 'bg-gray-100 dark:bg-gray-850'
							: 'hover:bg-gray-50 dark:hover:bg-gray-900'}"
						on:click={() => selectCourse(course.id)}
					>
						<div class="text-sm font-medium">{course.name}</div>
					</button>
				{:else}
					<div class="text-sm text-gray-500 px-3 py-2">{$i18n.t('No courses yet')}</div>
				{/each}
			</div>
		</div>

		<!-- Course detail -->
		<div class="md:w-2/3 w-full flex flex-col gap-3">
			{#if selectedCourse}
				<div class="flex items-start justify-between">
					<div>
						<div class="text-lg font-medium">{selectedCourse.name}</div>
					</div>
					<button
						class="px-2.5 py-1 text-sm rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
						on:click={() => deleteHandler(selectedCourse.id)}>{$i18n.t('Delete')}</button
					>
				</div>

				<div class="flex items-center justify-between">
					<div class="text-sm font-medium">{$i18n.t('Materials')}</div>
					<button
						class="px-2.5 py-1 text-sm rounded-lg bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition flex items-center gap-1.5"
						on:click={() => fileInputElement?.click()}
						disabled={uploading}
					>
						{#if uploading}<Spinner className="size-3.5" />{/if}
						{$i18n.t('Upload material')}
					</button>
					<input
						bind:this={fileInputElement}
						type="file"
						class="hidden"
						on:change={uploadHandler}
					/>
				</div>

				<div class="flex flex-col gap-1 overflow-y-auto">
					{#each selectedCourse.files ?? [] as file (file.id)}
						<div
							class="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-900"
						>
							<div class="text-sm truncate">
								{file?.meta?.name ?? file?.filename ?? file.id}
							</div>
							<button
								class="text-xs text-red-500 hover:underline"
								on:click={() => removeFileHandler(file.id)}>{$i18n.t('Remove')}</button
							>
						</div>
					{:else}
						<div class="text-sm text-gray-500 px-3 py-2">
							{$i18n.t('No materials uploaded yet')}
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-sm text-gray-500 flex items-center justify-center h-full">
					{$i18n.t('Select a course to manage its materials')}
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="flex h-full items-center justify-center">
		<Spinner />
	</div>
{/if}
