// 36 PPT themes adapted from video-ppt-front
// Each theme maps to 知伴's 4-color palette: [primary, secondary, accent, paper/bg]
// Plus metadata for the picker UI

export const PPT_THEMES = [
  { id: 'minimal-white', label: '极简白', category: '通用', palette: ['#111216', '#3b3f4a', '#6b6f7a', '#ffffff'], dark: false, desc: '克制高级,百搭不挑内容' },
  { id: 'academic-paper', label: '学术论文', category: '教学', palette: ['#1a3a7a', '#0a0a0a', '#8a1a1a', '#fdfcf8'], dark: false, desc: '偏暖底色的学术风格' },
  { id: 'arctic-cool', label: '北极冷调', category: '商务', palette: ['#1e6fb0', '#17b1b1', '#6f8aa6', '#f2f6fb'], dark: false, desc: '清凉冷静的蓝调' },
  { id: 'aurora', label: '极光', category: '创意', palette: ['#5ef2c6', '#7aa2ff', '#c984ff', '#06091c'], dark: true, desc: '深色星空极光渐变' },
  { id: 'bauhaus', label: '包豪斯', category: '创意', palette: ['#e03c27', '#f4c430', '#1d4eaf', '#f4efe3'], dark: false, desc: '经典红黄蓝三原色' },
  { id: 'blueprint', label: '蓝图', category: '技术', palette: ['#ffffff', '#aee1ff', '#ffd27a', '#0b3a6f'], dark: true, desc: '工程蓝图风格,白线深蓝底' },
  { id: 'catppuccin-latte', label: 'Catppuccin Latte', category: '通用', palette: ['#8839ef', '#1e66f5', '#ea76cb', '#eff1f5'], dark: false, desc: '温暖柔和的浅色主题' },
  { id: 'catppuccin-mocha', label: 'Catppuccin Mocha', category: '通用', palette: ['#cba6f7', '#89b4fa', '#f5c2e7', '#1e1e2e'], dark: true, desc: '温暖柔和的深色主题' },
  { id: 'corporate-clean', label: '企业洁净', category: '商务', palette: ['#0a2540', '#1d4ed8', '#64748b', '#ffffff'], dark: false, desc: '专业商务,干净利落' },
  { id: 'cyberpunk-neon', label: '赛博朋克', category: '创意', palette: ['#ff2bd6', '#00f0ff', '#f9f871', '#000000'], dark: true, desc: '霓虹灯效,赛博美学' },
  { id: 'dracula', label: 'Dracula', category: '技术', palette: ['#bd93f9', '#ff79c6', '#8be9fd', '#282a36'], dark: true, desc: '经典暗色开发者主题' },
  { id: 'editorial-serif', label: '编辑衬线', category: '教学', palette: ['#8a2a1c', '#c97a4a', '#1b1410', '#faf7f2'], dark: false, desc: '书卷气,适合长文阅读' },
  { id: 'engineering-whiteprint', label: '工程白图', category: '技术', palette: ['#0a1e46', '#1e5ac4', '#c42a10', '#ffffff'], dark: false, desc: '工程图纸般的精准感' },
  { id: 'glassmorphism', label: '玻璃态', category: '创意', palette: ['#7dd3fc', '#c084fc', '#f0abfc', '#0b1024'], dark: true, desc: '毛玻璃质感,现代轻盈' },
  { id: 'gruvbox-dark', label: 'Gruvbox Dark', category: '技术', palette: ['#fe8019', '#fabd2f', '#b8bb26', '#282828'], dark: true, desc: '复古暖色暗调' },
  { id: 'japanese-minimal', label: '日式极简', category: '教学', palette: ['#d93a2a', '#1a1a18', '#c9a961', '#fafaf5'], dark: false, desc: '和风侘寂,留白美学' },
  { id: 'magazine-bold', label: '杂志粗体', category: '商务', palette: ['#ea5a1a', '#0a0a0a', '#c42a10', '#f5efe2'], dark: false, desc: '大胆对比,冲击力强' },
  { id: 'memphis-pop', label: '孟菲斯波普', category: '创意', palette: ['#ff3d8b', '#37c2d7', '#ffcc00', '#fef6e8'], dark: false, desc: '80年代孟菲斯风格' },
  { id: 'midcentury', label: '中世纪现代', category: '创意', palette: ['#d4902a', '#2a7a7f', '#c7502a', '#f3ead8'], dark: false, desc: '50-60年代复古现代主义' },
  { id: 'neo-brutalism', label: '新粗野主义', category: '创意', palette: ['#ffd400', '#ff5ca8', '#3a7cff', '#fffef0'], dark: false, desc: '粗黑边框+高饱和撞色' },
  { id: 'news-broadcast', label: '新闻广播', category: '商务', palette: ['#e11d2d', '#0a0a0a', '#ffd100', '#ffffff'], dark: false, desc: '电视新闻标题风格' },
  { id: 'nord', label: 'Nord', category: '技术', palette: ['#88c0d0', '#81a1c1', '#b48ead', '#2e3440'], dark: true, desc: '北极蓝灰暗色调' },
  { id: 'pitch-deck-vc', label: 'VC 路演', category: '商务', palette: ['#0070f3', '#7928ca', '#ff4ecb', '#ffffff'], dark: false, desc: '创业路演风格,现代感强' },
  { id: 'rainbow-gradient', label: '彩虹渐变', category: '创意', palette: ['#ff4d8b', '#7a5cff', '#36b6ff', '#ffffff'], dark: false, desc: '多彩彩虹渐变装饰' },
  { id: 'retro-tv', label: '复古电视', category: '创意', palette: ['#c73a1f', '#e67e14', '#f2b544', '#f5ecd7'], dark: false, desc: 'CRT电视的温暖复古感' },
  { id: 'rose-pine', label: 'Rose Pine', category: '通用', palette: ['#ebbcba', '#c4a7e7', '#9ccfd8', '#191724'], dark: true, desc: '玫瑰松木温柔暗色' },
  { id: 'sharp-mono', label: '锐利等宽', category: '技术', palette: ['#000000', '#000000', '#ff2200', '#ffffff'], dark: false, desc: '极致黑白,仅红色点缀' },
  { id: 'soft-pastel', label: '柔和粉彩', category: '教学', palette: ['#f49bb8', '#b5d5f0', '#f7d08a', '#fdf7fb'], dark: false, desc: '温柔粉嫩,适合轻松内容' },
  { id: 'solarized-light', label: 'Solarized Light', category: '技术', palette: ['#268bd2', '#2aa198', '#d33682', '#fdf6e3'], dark: false, desc: '经典护眼暖白底色' },
  { id: 'sunset-warm', label: '日落暖调', category: '通用', palette: ['#d94860', '#e36a2d', '#f2a341', '#fff7ef'], dark: false, desc: '温暖落日橙红渐变' },
  { id: 'swiss-grid', label: '瑞士网格', category: '商务', palette: ['#d6001c', '#111111', '#888888', '#ffffff'], dark: false, desc: '瑞士国际主义平面设计' },
  { id: 'terminal-green', label: '终端绿屏', category: '技术', palette: ['#00ff88', '#67ffd0', '#b6ff6b', '#030a04'], dark: true, desc: '复古终端绿色荧光' },
  { id: 'tokyo-night', label: '东京之夜', category: '技术', palette: ['#7aa2f7', '#bb9af7', '#7dcfff', '#1a1b26'], dark: true, desc: '东京夜晚的霓虹蓝紫' },
  { id: 'vaporwave', label: '蒸汽波', category: '创意', palette: ['#ff6ec7', '#00f5ff', '#ffd166', '#1a0938'], dark: true, desc: '80年代复古未来主义' },
  { id: 'xiaohongshu-white', label: '小红书白', category: '教学', palette: ['#ff2742', '#ff7a90', '#ffb38a', '#fffdfb'], dark: false, desc: '生活分享风格,温暖柔和' },
  { id: 'y2k-chrome', label: 'Y2K 铬色', category: '创意', palette: ['#8a5cff', '#3ccfd8', '#ff84c4', '#dfe4ec'], dark: false, desc: '千禧年金属质感' }
]

export const THEME_CATEGORIES = ['全部', '通用', '商务', '教学', '技术', '创意']

export function getThemeById(id) {
  return PPT_THEMES.find(t => t.id === id) || PPT_THEMES[0]
}

export function getDefaultTheme() {
  return PPT_THEMES[0]
}
