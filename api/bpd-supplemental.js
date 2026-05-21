const CKAN_SQL_URL = 'https://data.boston.gov/api/3/action/datastore_search_sql';
const SHOTS_FIRED_RESOURCE_ID = 'c1e4e6ac-8a84-4b48-8a23-7b2645a32ede';
const SHOOTINGS_RESOURCE_ID = '73c7e069-701f-4910-986d-b950f46c91a1';
const SHOTS_FIRED_SOURCE_URL = `https://data.boston.gov/dataset/shots-fired/resource/${SHOTS_FIRED_RESOURCE_ID}`;
const SHOOTINGS_SOURCE_URL = `https://data.boston.gov/dataset/shootings/resource/${SHOOTINGS_RESOURCE_ID}`;

const DISTRICTS = {
  A1: 'Downtown / Beacon Hill / Chinatown / North End',
  A15: 'Charlestown',
  A7: 'East Boston',
  B2: 'Roxbury / Mission Hill',
  B3: 'Mattapan',
  C6: 'South Boston',
  C11: 'Dorchester',
  D4: 'Back Bay / Fenway / South End',
  D14: 'Allston / Brighton',
  E5: 'West Roxbury / Roslindale',
  E13: 'Jamaica Plain',
  E18: 'Hyde Park',
};

const CENTROIDS = {
  A1: [42.3577, -71.0609],
  A15: [42.3782, -71.0602],
  A7: [42.3752, -71.0316],
  B2: [42.3289, -71.0851],
  B3: [42.2838, -71.0916],
  C6: [42.3334, -71.0442],
  C11: [42.3064, -71.0592],
  D4: [42.3447, -71.0842],
  D14: [42.3507, -71.1527],
  E5: [42.2854, -71.1538],
  E13: [42.3132, -71.1141],
  E18: [42.2557, -71.1245],
};

function parseDate(raw) {
  if (!raw) return null;
  return new Date(raw.replace('+00', 'Z'));
}

function normalizeShots(rec) {
  const district = String(rec.district || 'UNK').trim().toUpperCase() || 'UNK';
  const coords = CENTROIDS[district];
  const occurred = parseDate(rec.incident_date);
  if (!coords || !occurred || Number.isNaN(occurred.getTime())) return null;
  const incident = String(rec.incident_num || `shots-fired-${rec._id}`).trim();
  const ballistic = String(rec.ballistics_evidence || '').toLowerCase() === 't';
  const evidenceNote = ballistic ? '; ballistic evidence recovered' : '';
  return {
    story_id: `bpd-shots-fired-${incident}`,
    incident_number: `bpd-shots-fired-${incident}`,
    headline: 'Official BPD shots fired report',
    title: 'Official BPD shots fired report',
    description: `Shots fired report — district-level location only (${district}: ${DISTRICTS[district] || district}${evidenceNote}).`,
    source_name: 'Boston Police Department Shots Fired open data',
    source_url: SHOTS_FIRED_SOURCE_URL,
    attribution: 'Boston Police Department / Analyze Boston',
    district,
    shooting: true,
    occurred_on: occurred.toISOString(),
    occurred_ts: Math.floor(occurred.getTime() / 1000),
    day_of_week: occurred.toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' }),
    hour: occurred.getUTCHours(),
    street: `District ${district} centroid (approximate)`,
    lat: coords[0],
    lng: coords[1],
    category: 'shooting',
    bucket: 'violent',
    mappable: true,
    location_precision: 'district_centroid',
    raw_source: 'shots_fired',
  };
}

function normalizeShooting(rec) {
  const district = String(rec.district || 'UNK').trim().toUpperCase() || 'UNK';
  const coords = CENTROIDS[district];
  const occurred = parseDate(rec.shooting_date);
  if (!coords || !occurred || Number.isNaN(occurred.getTime())) return null;
  const incident = String(rec.incident_num || `shooting-${rec._id}`).trim();
  const kind = String(rec.shooting_type_v2 || 'Shooting').trim() || 'Shooting';
  const multi = String(rec.multi_victim || '').toLowerCase() === 't';
  const multiNote = multi ? '; multi-victim incident' : '';
  return {
    story_id: `bpd-shooting-${incident}`,
    incident_number: `bpd-shooting-${incident}`,
    headline: `Official BPD ${kind.toLowerCase()} shooting report`,
    title: `Official BPD ${kind.toLowerCase()} shooting report`,
    description: `Official BPD ${kind.toLowerCase()} shooting — district-level location only (${district}: ${DISTRICTS[district] || district}${multiNote}).`,
    source_name: 'Boston Police Department Shootings open data',
    source_url: SHOOTINGS_SOURCE_URL,
    attribution: 'Boston Police Department / Analyze Boston',
    district,
    shooting: true,
    occurred_on: occurred.toISOString(),
    occurred_ts: Math.floor(occurred.getTime() / 1000),
    day_of_week: occurred.toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' }),
    hour: occurred.getUTCHours(),
    street: `District ${district} centroid (approximate)`,
    lat: coords[0],
    lng: coords[1],
    category: 'shooting',
    bucket: 'violent',
    mappable: true,
    location_precision: 'district_centroid',
    raw_source: 'shootings',
  };
}

async function fetchRows(resourceId, dateField, limit) {
  const sql = `SELECT * FROM "${resourceId}" ORDER BY "${dateField}" DESC NULLS LAST LIMIT ${Number(limit) || 500}`;
  const url = `${CKAN_SQL_URL}?${new URLSearchParams({ sql })}`;
  const resp = await fetch(url, { headers: { 'User-Agent': 'BostonCrimeMap/1.0' } });
  if (!resp.ok) throw new Error(`CKAN ${resp.status}`);
  const data = await resp.json();
  if (!data.success) throw new Error('CKAN failure');
  return data.result.records || [];
}

export default async function handler(req, res) {
  try {
    const days = Math.max(1, Math.min(3650, Number(req.query.days || 365)));
    const limit = Math.max(1, Math.min(1000, Number(req.query.limit || 500)));
    const category = String(req.query.category || '').toLowerCase();
    if (category && !['shooting', 'shootings'].includes(category)) {
      res.setHeader('Cache-Control', 's-maxage=1800, stale-while-revalidate=3600');
      return res.status(200).json({ count: 0, items: [], note: 'BPD supplemental datasets currently map shooting-related rows only.' });
    }
    const [shots, shootings] = await Promise.all([
      fetchRows(SHOTS_FIRED_RESOURCE_ID, 'incident_date', limit),
      fetchRows(SHOOTINGS_RESOURCE_ID, 'shooting_date', limit),
    ]);
    const cutoff = Date.now() - days * 86400 * 1000;
    const dedup = new Map();
    [...shots.map(normalizeShots), ...shootings.map(normalizeShooting)]
      .filter(Boolean)
      .filter((row) => new Date(row.occurred_on).getTime() >= cutoff)
      .forEach((row) => dedup.set(row.incident_number, row));
    const items = [...dedup.values()].sort((a, b) => b.occurred_ts - a.occurred_ts).slice(0, limit);
    res.setHeader('Cache-Control', 's-maxage=1800, stale-while-revalidate=3600');
    return res.status(200).json({
      count: items.length,
      items,
      cache: {
        bpd_supplemental: {
          record_count: items.length,
          shots_fired_raw_count: shots.length,
          shootings_raw_count: shootings.length,
          location_precision: 'district_centroid',
          sources: { shots_fired: SHOTS_FIRED_SOURCE_URL, shootings: SHOOTINGS_SOURCE_URL },
        },
      },
    });
  } catch (err) {
    return res.status(500).json({ error: 'bpd_supplemental_unavailable', message: err.message });
  }
}
