/**
 * ТТС-Север: уведомления, AJAX в тех. панели, фоновое обновление заявок (polling).
 */
(function () {
    function fadeOut(el) {
        if (!el || el.dataset.dismissed) return;
        el.dataset.dismissed = '1';
        el.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-6px)';
        setTimeout(function () {
            var parent = el.parentNode;
            el.remove();
            if (
                parent &&
                parent.classList &&
                parent.classList.contains('alerts') &&
                parent.children.length === 0
            ) {
                parent.remove();
            }
        }, 260);
    }

    /** Обновить карточку из объекта строки API / ответа сохранения */
    function applyRowToCard(card, row) {
        var locked = card.getAttribute('data-locked') === '1';
        var badge = card.querySelector('[data-role="status-badge"]');
        if (badge && row.status_display && row.status) {
            badge.textContent = row.status_display;
            badge.className = 'badge badge-' + row.status;
        }
        var commentText = card.querySelector('[data-role="comment-text"]');
        var commentLine = card.querySelector('[data-role="comment-line"]');
        if (commentText && typeof row.comment === 'string') {
            commentText.textContent = row.comment;
            if (commentLine) commentLine.hidden = !row.comment;
        }
        var assignedLine = card.querySelector('[data-role="assigned-line"]');
        var assignedName = card.querySelector('[data-role="assigned-name"]');
        if (assignedLine && assignedName && typeof row.assigned_to === 'string') {
            assignedName.textContent = row.assigned_to;
            assignedLine.hidden = !row.assigned_to;
        }
        if (locked) return;
        var sel = card.querySelector('select[name="action"]');
        if (sel && document.activeElement !== sel && row.status) {
            sel.value = row.status;
        }
        var ta = card.querySelector('textarea[name="comment"]');
        if (ta && document.activeElement !== ta && typeof row.comment === 'string') {
            ta.value = row.comment;
        }
    }

    function getCookie(name) {
        var m = document.cookie.match(
            '(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'
        );
        return m ? decodeURIComponent(m[1]) : '';
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.alerts .alert').forEach(function (el) {
            el.setAttribute('title', 'Нажмите, чтобы закрыть');
            el.addEventListener('click', function () {
                fadeOut(el);
            });
            if (el.classList.contains('success')) {
                window.setTimeout(function () {
                    fadeOut(el);
                }, 5500);
            }
        });
    });

    document.addEventListener('DOMContentLoaded', function () {
        var root = document.querySelector('[data-tech-update-url]');
        if (!root) return;
        var updateUrl = root.getAttribute('data-tech-update-url');
        var csrftoken = getCookie('csrftoken');

        root.querySelectorAll('form.tech-request-form[data-tech-ajax="1"]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                var card = form.closest('[data-request-pk]');
                if (!card) return;
                var badge = card.querySelector('[data-role="status-badge"]');
                var btn = form.querySelector('[data-role="save-btn"]');
                var hint = form.querySelector('[data-role="save-hint"]');
                var fd = new FormData(form);
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'Сохранение…';
                }
                if (hint) hint.hidden = true;

                fetch(updateUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: fd,
                    credentials: 'same-origin',
                })
                    .then(function (r) {
                        return r.text().then(function (text) {
                            var data;
                            try {
                                data = JSON.parse(text);
                            } catch (err) {
                                data = {
                                    ok: false,
                                    error: 'Ответ сервера не JSON. Обновите страницу.',
                                };
                            }
                            return { ok: r.ok, status: r.status, data: data };
                        });
                    })
                    .then(function (res) {
                        if (!res.ok || !res.data.ok) {
                            var msg =
                                (res.data && res.data.error) ||
                                'Не удалось сохранить (' + res.status + ')';
                            window.alert(msg);
                            return;
                        }
                        var d = res.data;
                        applyRowToCard(card, {
                            status: d.status,
                            status_display: d.status_display,
                            comment: d.comment,
                            assigned_to: d.assigned_to,
                        });
                        if (d.hide) {
                            card.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
                            card.style.opacity = '0';
                            card.style.transform = 'translateY(6px)';
                            window.setTimeout(function () {
                                card.remove();
                                if (!root.querySelector('[data-request-pk]')) {
                                    window.location.reload();
                                }
                            }, 240);
                        } else if (hint) {
                            hint.hidden = false;
                            window.setTimeout(function () {
                                hint.hidden = true;
                            }, 2200);
                        }
                    })
                    .catch(function () {
                        window.alert('Ошибка сети. Проверьте подключение и попробуйте снова.');
                    })
                    .finally(function () {
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'Сохранить';
                        }
                    });
            });
        });
    });

    document.addEventListener('DOMContentLoaded', function () {
        var section = document.querySelector('[data-requests-poll][data-requests-api-url]');
        if (!section) return;
        var scope = section.getAttribute('data-requests-poll');
        var apiBase = section.getAttribute('data-requests-api-url');
        if (!apiBase || !scope) return;

        var paused = false;
        document.addEventListener('visibilitychange', function () {
            paused = document.hidden;
        });

        var intervalMs = parseInt(
            section.getAttribute('data-requests-poll-interval') || '7000',
            10
        );
        if (!Number.isFinite(intervalMs) || intervalMs < 4000) {
            intervalMs = 7000;
        }

        var tvPollSecret = section.getAttribute('data-tv-secret') || '';

        function pollUrl() {
            var u = new URL(apiBase, window.location.origin);
            new URLSearchParams(window.location.search).forEach(function (v, k) {
                if (k !== 'scope' && k !== 'tv_secret') u.searchParams.set(k, v);
            });
            u.searchParams.set('scope', scope);
            if (scope === 'tv' && tvPollSecret) {
                u.searchParams.set('tv_secret', tvPollSecret);
            }
            return u.toString();
        }

        function pollTick() {
            if (paused) return;
            fetch(pollUrl(), { credentials: 'same-origin' })
                .then(function (r) {
                    return r.text().then(function (text) {
                        try {
                            return { ok: r.ok, data: JSON.parse(text) };
                        } catch (e) {
                            return { ok: false, data: null };
                        }
                    });
                })
                .then(function (res) {
                    if (!res.ok || !res.data || !Array.isArray(res.data.requests)) return;
                    var rows = res.data.requests;
                    var cards = section.querySelectorAll('[data-request-pk]');

                    if (rows.length !== cards.length) {
                        window.location.reload();
                        return;
                    }

                    var byId = {};
                    rows.forEach(function (x) {
                        byId[x.id] = x;
                    });

                    for (var i = 0; i < cards.length; i++) {
                        var card = cards[i];
                        var id = parseInt(card.getAttribute('data-request-pk'), 10);
                        var row = byId[id];
                        if (!row) {
                            window.location.reload();
                            return;
                        }
                        if (scope === 'tech' && typeof row.locked_for_me === 'boolean') {
                            var domLocked = card.getAttribute('data-locked') === '1';
                            if (row.locked_for_me !== domLocked) {
                                window.location.reload();
                                return;
                            }
                        }
                        applyRowToCard(card, row);
                    }
                })
                .catch(function () {});
        }

        pollTick();
        window.setInterval(pollTick, intervalMs);
    });

    document.addEventListener('DOMContentLoaded', function () {
        var clock = document.getElementById('tv-clock');
        if (!clock) return;
        function tick() {
            var d = new Date();
            clock.textContent = d.toLocaleString('ru-RU', {
                weekday: 'short',
                day: 'numeric',
                month: 'long',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
            clock.setAttribute('datetime', d.toISOString());
        }
        tick();
        window.setInterval(tick, 1000);
    });
})();

