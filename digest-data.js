'use strict';
// Immutable issue files are loaded directly; publishing never retransmits the archive.
window.DIGEST_DATA = {manifest:{issues:[]},issues:[]};
window.DIGEST_READY = (async () => {
  const get = async path => {
    const response = await fetch(path, {cache:'no-cache'});
    if (!response.ok) throw new Error(`Unable to load ${path}: ${response.status}`);
    return response.json();
  };
  const manifest = await get('digest/manifest.json');
  const issues = await Promise.all(manifest.issues.map(async entry => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(entry.date)) throw new Error('Invalid issue date');
    const issue = await get(`digest/issues/${entry.date}.json`);
    if (issue.date !== entry.date || issue.papers.length !== entry.count) throw new Error('Issue index mismatch');
    return issue;
  }));
  Object.assign(window.DIGEST_DATA, {manifest, issues});
})().catch(error => {window.DIGEST_LOAD_ERROR=error;});
