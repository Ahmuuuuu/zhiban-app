const backgroundModules = import.meta.glob('../../../assets/ppt_video/ppt/backgrounds/*.{png,jpg,jpeg,webp}', {
  eager: true,
  query: '?url',
  import: 'default'
})

const decorationModules = import.meta.glob('../../../assets/ppt_video/ppt/decorations/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  query: '?url',
  import: 'default'
})

const subjectModules = import.meta.glob('../../../assets/ppt_video/ppt/subjects/**/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  query: '?url',
  import: 'default'
})

const splitPath = p => p.split(/[/\\]/)

const toAssetList = modules => Object.entries(modules)
  .map(([path, url]) => {
    const segments = splitPath(path)
    return {
      path,
      url,
      name: decodeURIComponent(segments.pop() || ''),
      group: decodeURIComponent(segments.pop() || '')
    }
  })
  .sort((a, b) => a.path.localeCompare(b.path, 'zh-Hans-CN'))

const backgrounds = toAssetList(backgroundModules)
const decorations = toAssetList(decorationModules)
const subjects = toAssetList(subjectModules)

const hashText = value => {
  const text = String(value || '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  }
  return hash
}

const pick = (list, seed, offset = 0) => {
  if (!list.length) return null
  return list[(hashText(seed) + offset) % list.length]
}

const includesAny = (text, words) => words.some(word => text.includes(word.toLowerCase()))

const subjectRules = [
  {
    key: '\u5fae\u673a\u539f\u7406',
    words: ['\u5fae\u673a', '\u5355\u7247\u673a', '\u82af\u7247', '\u7535\u8def\u677f', '\u5bc4\u5b58\u5668', '\u6c47\u7f16', 'cpu', '\u603b\u7ebf']
  },
  {
    key: '\u8ba1\u7b97\u673a',
    words: ['\u8ba1\u7b97\u673a', '\u7535\u8111', '\u7f16\u7a0b', '\u7a0b\u5e8f', '\u7b97\u6cd5', '\u6570\u636e\u7ed3\u6784', '\u7f51\u7edc', '\u8f6f\u4ef6', '\u4ee3\u7801', 'ai', '\u4eba\u5de5\u667a\u80fd']
  },
  {
    key: '\u6570\u5b66',
    words: ['\u6570\u5b66', '\u51fd\u6570', '\u516c\u5f0f', '\u51e0\u4f55', '\u4ee3\u6570', '\u5fae\u79ef\u5206', '\u6982\u7387', '\u7edf\u8ba1', '\u65b9\u7a0b']
  },
  {
    key: '\u7269\u7406',
    words: ['\u7269\u7406', '\u529b\u5b66', '\u7535\u8def', '\u7535\u78c1', '\u5149\u5b66', '\u70ed\u5b66', '\u5b9e\u9a8c', '\u4eea\u5668']
  },
  {
    key: '\u5316\u5b66',
    words: ['\u5316\u5b66', '\u5206\u5b50', '\u539f\u5b50', '\u8bd5\u7ba1', '\u53cd\u5e94', '\u6eb6\u6db2', '\u5b9e\u9a8c', '\u5143\u7d20']
  },
  {
    key: '\u751f\u7269',
    words: ['\u751f\u7269', '\u7ec6\u80de', '\u690d\u7269', '\u57fa\u56e0', 'dna', '\u8840\u7ba1', '\u751f\u6001', '\u751f\u547d']
  },
  {
    key: '\u82f1\u8bed',
    words: ['\u82f1\u8bed', '\u82f1\u6587', '\u5355\u8bcd', '\u8bed\u6cd5', '\u9605\u8bfb', '\u5199\u4f5c', '\u542c\u529b', '\u53e3\u8bed', 'english']
  },
  {
    key: '\u5386\u53f2',
    words: ['\u5386\u53f2', '\u671d\u4ee3', '\u53e4\u4ee3', '\u8fd1\u4ee3', '\u6218\u4e89', '\u6587\u660e', '\u65f6\u95f4\u7ebf']
  },
  {
    key: '\u5730\u7406',
    words: ['\u5730\u7406', '\u5730\u56fe', '\u5730\u7403', '\u5c71\u5ddd', '\u6c14\u5019', '\u5730\u8c8c', '\u7ecf\u7eac', '\u533a\u57df']
  }
]

const themeSubjectFallback = {
  science_green: '生物',
  graphite: '计算机',
  warm_case: '历史'
}

const inferSubject = slide => {
  const text = `${slide?.title || ''}\n${slide?.text || ''}\n${slide?.content || ''}`.toLowerCase()
  const regexMatch = subjectRules.find(item => includesAny(text, item.words))
  if (regexMatch) return regexMatch.key

  const visual = (slide?.visual?.query || slide?.visual_hint || '').toLowerCase()
  if (visual) {
    const visualMatch = subjectRules.find(item => includesAny(visual, item.words))
    if (visualMatch) return visualMatch.key
  }

  return themeSubjectFallback[slide?.theme] || ''
}

const decorationWords = {
  tape: ['\u7eb8\u80f6\u5e26', '\u80f6\u5e26', 'tape'],
  note: ['\u4fbf\u7b7e', 'note', 'paper'],
  pin: ['\u56fe\u9489', 'pin'],
  clip: ['\u5939\u5b50', 'clip'],
  highlight: ['\u5212\u7ebf', '\u8367\u5149', 'highlight', 'line']
}

const byDecoration = type => decorations.filter(item => includesAny(item.name.toLowerCase(), decorationWords[type] || []))
const bySubject = subject => subjects.filter(item => item.group === subject)

const normalizeSubject = value => {
  const text = String(value || '').trim().toLowerCase()
  if (!text) return ''
  const direct = subjectRules.find(item => item.key.toLowerCase() === text)
  if (direct) return direct.key
  const keyword = subjectRules.find(item => includesAny(text, [item.key, ...item.words]))
  return keyword?.key || ''
}

const pickSubjectAsset = (list, slide, seed) => {
  if (!list.length) return null
  const text = `${slide?.title || ''}\n${slide?.text || ''}\n${slide?.content || ''}`.toLowerCase()
  const matched = list.find(item => text.includes(item.name.replace(/\.[^.]+$/, '').toLowerCase()))
  return matched || pick(list, seed)
}

export const selectCustomPptAssets = (slide, index = 0) => {
  const seed = `${slide?.title || ''}-${slide?.text || slide?.content || ''}-${index}`
  const subject = normalizeSubject(slide?.subject || slide?.discipline || slide?.courseSubject) || inferSubject(slide)
  const subjectList = subject ? bySubject(subject) : []
  const background = backgrounds.length ? backgrounds[index % backgrounds.length] : null

  return {
    background: background?.url || '',
    subject,
    subjectImage: pickSubjectAsset(subjectList, slide, seed)?.url || '',
    tape: pick(byDecoration('tape'), seed)?.url || '',
    note: pick(byDecoration('note'), seed, 1)?.url || '',
    pin: pick(byDecoration('pin'), seed, 2)?.url || '',
    clip: pick(byDecoration('clip'), seed, 3)?.url || '',
    highlight: pick(byDecoration('highlight'), seed, 4)?.url || ''
  }
}

export const customPptAssetStats = {
  backgrounds: backgrounds.length,
  decorations: decorations.length,
  subjects: subjects.length
}
