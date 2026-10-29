export function receiveRawThread(current, data) {
  return {
    ...current, ...data,
    rawScript: data.raw_script ?? data.script,
    rawSession: data.session,
    script: data.edited_script ?? data.script ?? '', approved: false,
    rows: [], beats: [], frame: null, output: null, selected: 0,
    note: '',
  }
}

export function receiveReviewedThread(current, data) {
  return { ...current, ...data, approved: true, output: null, frame: null, selected: 0 }
}

export function editorialInput(draft) {
  return { session: draft.rawSession || '', script: draft.rawScript || '', content: draft.content || '' }
}
