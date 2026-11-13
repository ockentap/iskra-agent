import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import relativeDocLinks from './src/remark/relativeDocLinks';

const config: Config = {
  title: 'Iskra',
  tagline: 'The self-improving AI agent',
  favicon: 'img/favicon.ico',

  // GitHub Pages project site: https://ockentap.github.io/iskra-agent/
  url: 'https://ockentap.github.io',
  baseUrl: '/iskra-agent/',

  organizationName: 'ockentap',
  projectName: 'iskra-agent',

  onBrokenLinks: 'warn',
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  headTags: [
    {
      tagName: 'link',
      attributes: {rel: 'apple-touch-icon', href: '/iskra-agent/img/apple-touch-icon.png'},
    },
    {tagName: 'meta', attributes: {name: 'theme-color', content: '#0B0908'}},
    {
      tagName: 'meta',
      attributes: {
        name: 'description',
        content:
          'Iskra — the self-improving AI agent. A spark of a fork of Hermes Agent: a built-in learning loop that creates skills from experience and remembers across sessions.',
      },
    },
  ],

  themes: [
    '@docusaurus/theme-mermaid',
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        language: ['en'],
        indexDocs: true,
        indexBlog: false,
        indexPages: false,
        docsRouteBasePath: '/docs',
      },
    ],
  ],
  plugins: [
    [
      '@docusaurus/plugin-client-redirects',
      {
        redirects: [
          {from: '/docs/guides/automation-templates', to: '/docs/guides/automation-blueprints'},
          {from: '/docs/guides/build-a-hermes-plugin', to: '/docs/developer-guide/plugins'},
          {from: '/docs/quickstart', to: '/docs/getting-started/quickstart'},
          {from: '/docs/installation', to: '/docs/getting-started/installation'},
        ],
      },
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/ockentap/iskra-agent/edit/iskra-rebrand/website/',
          beforeDefaultRemarkPlugins: [[relativeDocLinks, {siteDir: __dirname}]],
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/iskra-banner.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: false,
      disableSwitch: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'Iskra',
      logo: {alt: 'Iskra', src: 'img/logo.svg'},
      items: [
        {type: 'docSidebar', sidebarId: 'docs', position: 'left', label: 'Docs'},
        {to: '/skills', label: 'Skills', position: 'left'},
        {to: '/docs/getting-started/installation', label: 'Install', position: 'left'},
        {href: 'https://github.com/ockentap/iskra-agent', label: 'GitHub', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Getting Started', to: '/docs/getting-started/quickstart'},
            {label: 'User Guide', to: '/docs/user-guide/cli'},
            {label: 'Developer Guide', to: '/docs/developer-guide/architecture'},
            {label: 'Reference', to: '/docs/reference/cli-commands'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub', href: 'https://github.com/ockentap/iskra-agent'},
            {label: 'Issues', href: 'https://github.com/ockentap/iskra-agent/issues'},
            {label: 'Skills Hub', href: 'https://agentskills.io'},
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'Install', to: '/docs/getting-started/installation'},
            {label: 'Upstream Hermes', href: 'https://github.com/NousResearch/hermes-agent'},
          ],
        },
      ],
      copyright: `Iskra — a fork of <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> by Nous Research · MIT License · ${new Date().getFullYear()}`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'json', 'python', 'toml'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,
};

export default config;