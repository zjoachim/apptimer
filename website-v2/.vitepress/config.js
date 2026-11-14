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
          { text: '最新版（Windows 10/11）', link: '/AppTimer-v3.zip' },
          { text: 'v2（Win11，旧版）', link: '/AppTimer-v2.exe' },
          { text: 'v1（Win10，旧版）', link: '/AppTimer-v1.exe' },
          { text: 'GitHub Releases', link: 'https://github.com/zjoachim/apptimer/releases' },
        ],
      },
    ],

    sidebar: {
      '/guide': [
        {
          text: '使用指南',
          items: [
            { text: '安装与启动', link: '/guide#安装与启动' },
            { text: '界面概览', link: '/guide#界面概览' },
            { text: '计时与记录', link: '/guide#计时与记录' },
            { text: '数据与报表', link: '/guide#数据与报表' },
            { text: '分类与别名', link: '/guide#分类与别名' },
            { text: '番茄钟与每日目标', link: '/guide#番茄钟与每日目标' },
            { text: '设置与自启动', link: '/guide#设置与自启动' },
            { text: '版本区别', link: '/guide#版本区别' },
          ],
        },
      ],
    },

    socialLinks: [],

    footer: {
      message: 'Windows 程序使用时间追踪器',
      copyright: 'Copyright © 2026',
    },


  },
})
