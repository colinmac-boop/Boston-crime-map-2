import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 30000 });

export const fetchOverview = () => client.get("/stats/overview").then((r) => r.data);
export const fetchRecent = (limit = 12) =>
    client.get(`/incidents/recent?limit=${limit}`).then((r) => r.data);
export const fetchIncidents = (params = {}) =>
    client.get("/incidents", { params }).then((r) => r.data);
export const fetchNeighborhoods = () => client.get("/neighborhoods").then((r) => r.data);
export const fetchNeighborhood = (slug) =>
    client.get(`/neighborhoods/${slug}`).then((r) => r.data);
export const fetchCategories = () => client.get("/categories").then((r) => r.data);
export const fetchCategory = (slug) => client.get(`/categories/${slug}`).then((r) => r.data);
export const fetchWickedPicks = (limit = 6) =>
    client.get(`/wicked-picks?limit=${limit}`).then((r) => r.data);
export const fetchStories = (limit = 10, mappableOnly = false, params = {}) =>
    client.get("/stories", {
        params: { limit, mappable_only: mappableOnly, ...params },
    }).then((r) => r.data);

export const geocodeAddress = (q) =>
    client.get("/geocode", { params: { q } }).then((r) => r.data);

export const fetchIncidentsNear = ({ lat, lng, radius_mi = 0.5, days = 90, limit = 500 }) =>
    client.get("/incidents/near", { params: { lat, lng, radius_mi, days, limit } }).then((r) => r.data);
