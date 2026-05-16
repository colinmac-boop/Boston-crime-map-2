import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Masthead from "@/components/Masthead";
import Ticker from "@/components/Ticker";
import Footer from "@/components/Footer";
import ErrorBoundary from "@/components/ErrorBoundary";
import HomePage from "@/pages/HomePage";
import MapPage from "@/pages/MapPage";
import NeighborhoodsPage from "@/pages/NeighborhoodsPage";
import NeighborhoodDetail from "@/pages/NeighborhoodDetail";
import CategoryDetail from "@/pages/CategoryDetail";
import WickedPicksPage from "@/pages/WickedPicksPage";
import AboutPage from "@/pages/AboutPage";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

function ScrollToTop() {
    const { pathname } = useLocation();
    useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
    return null;
}

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <ScrollToTop />
                <Masthead />
                <Ticker />
                <ErrorBoundary>
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/map" element={<MapPage />} />
                        <Route path="/neighborhoods" element={<NeighborhoodsPage />} />
                        <Route path="/neighborhoods/:slug" element={<NeighborhoodDetail />} />
                        <Route path="/categories/:slug" element={<CategoryDetail />} />
                        <Route path="/wicked-picks" element={<WickedPicksPage />} />
                        <Route path="/about" element={<AboutPage />} />
                    </Routes>
                </ErrorBoundary>
                <Footer />
            </BrowserRouter>
        </div>
    );
}

export default App;
