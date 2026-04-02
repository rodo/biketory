package biketory;

import static io.gatling.javaapi.core.CoreDsl.*;

public class ReferralSimulation extends BaseSimulation {

    {
        setUp(
                referralSponsorPhase()
                        .injectOpen(atOnceUsers(4))
                        .andThen(
                                referralRefereePhase()
                                        .injectOpen(atOnceUsers(4))
                                        .andThen(
                                                referralVerifyPhase()
                                                        .injectOpen(atOnceUsers(4))
                                        )
                        )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
