import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'AppTimer',
  description: 'Windows 程序使用时间追踪器：按秒记录前台程序，数据只存本机',
  lang: 'zh-CN',
  base: '/',

  head: [['link', { rel: 'icon', href: '/favicon.svg' }]],

  appearance: 'dark',

  vite: {
    build: {
      rollupOptions: {
        external: [/^https:\/\/unpkg\.com\/three.*/]
      }
    }
  },

  themeConfig: {
    logo: null,

    nav: [
      { text: '首页', link: '/' },
      { text: '使用指南', link: '/guide' },
      { text: '常见问题', link: '/faq' },
      { text: '更新日志', link: '/changelog' },
      { text: '源代码', link: '/source' },
      { text: '反馈', link: 'https://github.com/zjoachim/apptimer/issues' },
      {
        text: '下载',
        items: [
          { text: '最新版（单文件，双击即用）', link: 'AppTimer-v3.exe' },
          { text: '便携目录版（解压后运行）', link: 'AppTimer-v3.zip' },
          { text: 'v2（Win11，旧版）', link: 'AppTimer-v2.exe' },
          { text: 'v1（Win10，旧版）', link: 'AppTimer-v1.exe' },
          { text: 'GitHub Releases', link: 'https://github.com/zjoachim/apptimer/releases' },
        ],
      },
    ],

    socialLinks: [],

    footer: {
      message: 'Windows 程序使用时间追踪器',
      copyright: 'Copyright © 2026',
    },


  },
})
