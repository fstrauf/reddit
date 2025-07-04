import dotenv from 'dotenv';
dotenv.config(); // Load .env file into process.env

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  modules: ["@nuxtjs/tailwindcss"],
  css: ["~/assets/css/tailwind.css"],
  
  // App metadata
  app: {
    head: {
      title: 'Reddit Sentiment Analyzer',
      meta: [
        { name: 'description', content: 'Discover business opportunities by analyzing sentiment and trends in Reddit communities' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ]
    }
  },
  
  runtimeConfig: {
    // Keys defined here are available server-side
    openaiApiKey: process.env.NUXT_OPENAI_API_KEY || process.env.OPENAI_API_KEY || '', // Explicitly read from process.env
    // Expose Reddit Credentials
    redditClientId: process.env.NUXT_REDDIT_CLIENT_ID || process.env.REDDIT_CLIENT_ID || '',
    redditClientSecret: process.env.NUXT_REDDIT_CLIENT_SECRET || process.env.REDDIT_CLIENT_SECRET || '',
    // Keys defined in public are available client-side
    public: {},
  },
})
