
(function () {
  var box = document.getElementById('lib-results');
  var q = document.getElementById('q');
  if (!box) return;
  var active = new Set();
  function boot(papers) {
    function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
    function fmt(d){var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      var p=(d||'').split('-'); if(p.length<3) return d; return m[+p[1]-1]+' '+(+p[2])+', '+p[0];}
    function render() {
      var term = (q.value || '').toLowerCase().trim();
      var rows = papers.filter(function (p) {
        for (var t of active) if ((p.tags || []).indexOf(t) < 0) return false;
        if (!term) return true;
        return (p.title + ' ' + (p.summary||'') + ' ' + (p.tags||[]).join(' ')).toLowerCase().indexOf(term) >= 0;
      });
      box.innerHTML = rows.slice(0, 300).map(function (p) {
        var badge = p.has_notes ? ' <span class="badge">notes</span>' : '';
        var au = p.audio ? ' <span class="badge audio">\u266a</span>' : '';
        return '<a class="read-row" href="papers/' + esc(p.id) + '.html"><time>' + fmt(p.date) +
          '</time><span class="read-title">' + esc(p.title) + badge + au + '</span></a>';
      }).join('') || '<p class="empty">No matches.</p>';
    }
    document.querySelectorAll('.tag-filter').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.getAttribute('data-tag');
        if (active.has(t)) { active.delete(t); b.classList.remove('on'); }
        else { active.add(t); b.classList.add('on'); }
        render();
      });
    });
    q.addEventListener('input', render);
    render();
  }
  if (window.__PAPERS__) boot(window.__PAPERS__);
  else fetch('papers.json').then(function (r) { return r.json(); }).then(boot);
})();
