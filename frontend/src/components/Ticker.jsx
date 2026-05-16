import Marquee from "react-fast-marquee";
import { TICKER_MESSAGES } from "@/lib/format";

export default function Ticker() {
    return (
        <div className="marquee-band" data-testid="ticker">
            <Marquee speed={42} gradient={false} pauseOnHover>
                {TICKER_MESSAGES.concat(TICKER_MESSAGES).map((m, i) => (
                    <span key={i}>
                        {m}
                        <span className="star">★</span>
                    </span>
                ))}
            </Marquee>
        </div>
    );
}
