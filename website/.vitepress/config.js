import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'AppTimer',
  description: 'Windows 程序使用时间追踪器',
  lang: 'zh-CN',
  base: '/apptimer/',

  themeConfig: {
    logo: null,

    nav: [
      { text: '首页', link: '/' },
      { text: '使用指南', link: '/guide' },
      { text: '常见问题', link: '/faq' },
      { text: '更新日志', link: '/changelog' },
      { text: '源代码', link: '/source' },
      {
        text: '下载',
        link: '/apptimer/AppTimer.exe',
      },
    ],

    sidebar: {
      '/guide': [
        {
          text: '使用指南',
          items: [
            { text: '安装与启动', link: '/guide#安装与启动' },
            { text: '界面概览', link: '/guide#界面概览' },
            { text: '追踪面板', link: '/guide#追踪面板' },
            { text: '分类标签', link: '/guide#分类标签' },
            { text: '数据与报表', link: '/guide#数据与报表' },
            { text: '设置与自启动', link: '/guide#设置与自启动' },
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
