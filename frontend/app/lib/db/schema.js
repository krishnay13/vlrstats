// Shared DB schema helpers (kept tiny + cached for perf)

let _matchesColumnsCache = null;

export function getMatchesColumns(db) {
  if (_matchesColumnsCache) return _matchesColumnsCache;
  const tableInfo = db.prepare('PRAGMA table_info(Matches)').all();
  _matchesColumnsCache = tableInfo.map((col) => col.name);
  return _matchesColumnsCache;
}

export function getMatchesDateMeta(db) {
  const columns = getMatchesColumns(db);
  return {
    hasMatchDate: columns.includes('match_date'),
    hasMatchTsUtc: columns.includes('match_ts_utc'),
  };
}

/**
 * Returns a SQL expression that yields a sortable "match date" string.
 * - If both columns exist: COALESCE(match_date, substr(match_ts_utc, 1, 10))
 * - If only match_ts_utc: match_ts_utc
 * - If only match_date: match_date
 */
export function getMatchDateExpr(dateMeta, prefix = '') {
  const p = prefix ? `${prefix}.` : '';
  const { hasMatchDate, hasMatchTsUtc } = dateMeta;

  if (hasMatchDate && hasMatchTsUtc) {
    return `COALESCE(${p}match_date, substr(${p}match_ts_utc, 1, 10))`;
  }
  if (hasMatchTsUtc) return `${p}match_ts_utc`;
  if (hasMatchDate) return `${p}match_date`;
  return null;
}

export function getMatchDateNonEmptyWhere(dateMeta, prefix = '') {
  const p = prefix ? `${prefix}.` : '';
  const { hasMatchDate, hasMatchTsUtc } = dateMeta;

  if (hasMatchDate && hasMatchTsUtc) {
    return `((${p}match_date IS NOT NULL AND ${p}match_date != '') OR (${p}match_ts_utc IS NOT NULL AND ${p}match_ts_utc != ''))`;
  }
  if (hasMatchTsUtc) {
    return `(${p}match_ts_utc IS NOT NULL AND ${p}match_ts_utc != '')`;
  }
  if (hasMatchDate) {
    return `(${p}match_date IS NOT NULL AND ${p}match_date != '')`;
  }
  return null;
}

