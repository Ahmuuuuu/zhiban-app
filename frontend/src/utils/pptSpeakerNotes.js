const NOTE_LABEL_RE = /^(?:\u8bb2\u7a3f|\u5907\u6ce8|\u6f14\u8bb2\u7a3f|speaker\s*notes?|speaker_notes?|notes?)\s*[:\uff1a]\s*(.*)$/i

const unwrapLine = line => String(line || '')
  .replace(/^\s*(?:[-*+\u2022]\s*)?/, '')
  .replace(/^\s*>\s?/, '')
  .trim()

const matchNoteLine = line => unwrapLine(line).match(NOTE_LABEL_RE)

export const splitSpeakerNotes = value => {
  const lines = String(value || '').split(/\r?\n/)
  const body = []
  const notes = []
  let readingQuotedNote = false

  for (const rawLine of lines) {
    const matched = matchNoteLine(rawLine)
    if (matched) {
      const noteText = matched[1]?.trim()
      if (noteText) notes.push(noteText)
      readingQuotedNote = /^\s*>/.test(rawLine)
      continue
    }

    if (readingQuotedNote && /^\s*>/.test(rawLine)) {
      const noteText = unwrapLine(rawLine)
      if (noteText) notes.push(noteText)
      continue
    }

    readingQuotedNote = false
    body.push(rawLine)
  }

  return {
    body: body.join('\n').trim(),
    notes: notes.join('\n').trim()
  }
}

export const stripSpeakerNotes = value => splitSpeakerNotes(value).body

export const mergeSpeakerNotes = (...values) => values
  .map(value => String(value || '').trim())
  .filter(Boolean)
  .join('\n')
