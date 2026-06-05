package org.ibo.nexusjava.modules.system.vo;

import lombok.Data;
import java.util.List;

@Data
public class ChartsVO {
    private List<PlatformDist> platformDistribution;
    private List<HourlyTrend> hourlyTrend;

    @Data
    public static class PlatformDist {
        private String platform;
        private Long count;
    }

    @Data
    public static class HourlyTrend {
        private String hour;
        private Long count;
    }
}
