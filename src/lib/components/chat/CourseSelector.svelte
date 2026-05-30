<script lang="ts">
	import { getContext } from 'svelte';
	import { courses, selectedCourse } from '$lib/stores';

	const i18n = getContext('i18n');

	const select = (course) => {
		// A course must always remain selected — no deselect.
		selectedCourse.set(course);
		localStorage.setItem('selectedCourseId', course.id);
	};
</script>

{#if ($courses ?? []).length > 0}
	<div class="flex items-center justify-start gap-1 overflow-x-auto scrollbar-none w-full">
		{#each $courses as course (course.id)}
			<button
				class="px-3 py-1 rounded-full text-sm whitespace-nowrap transition flex-none {$selectedCourse?.id ===
				course.id
					? 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white font-medium'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200'}"
				title={course.name}
				on:click={() => select(course)}
			>
				{course.name}
			</button>
		{/each}
	</div>
{/if}
