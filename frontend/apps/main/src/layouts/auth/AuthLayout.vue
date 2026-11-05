<template>
  <div class="h-screen overflow-y-auto overscroll-contain bg-secondary">
    <div class="flex min-h-full flex-col">
      <main class="flex flex-1 items-start justify-center px-4 pb-10 pt-[15vh] sm:px-6">
        <div class="auth-content w-full max-w-sm">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.auth-content > :deep(*) {
  border-radius: calc(var(--radius) + 0.25rem);
}
</style>
