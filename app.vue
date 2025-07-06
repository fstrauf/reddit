<template>
  <div>
    <nav class="bg-indigo-600 text-white p-4">
      <div class="max-w-7xl mx-auto flex justify-between items-center">
        <div class="text-xl font-bold">Reddit Sentiment Analyzer</div>
        <div class="flex space-x-6">
          <NuxtLink to="/" class="hover:text-indigo-200 transition-colors">Home</NuxtLink>
          <NuxtLink to="/python-analysis" class="hover:text-indigo-200 transition-colors">Python Analysis</NuxtLink>
        </div>
      </div>
    </nav>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </div>
</template>
