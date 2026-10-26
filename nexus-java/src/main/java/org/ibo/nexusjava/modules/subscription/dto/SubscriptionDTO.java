package org.ibo.nexusjava.modules.subscription.dto;

import jakarta.validation.constraints.*;
import jakarta.validation.Valid;
import lombok.Data;

import java.util.List;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionDTO {
    @NotBlank(message = "规则名称不能为空")
    @Size(max=100)
    private String name;
    @Size(max=20)
    private List<@Size(max=200) String> keywords;
    private List<String> sourcePlatforms;
    @Valid @Size(max=20)
    private List<@NotNull RssFeedItem> rssFeeds;
    private Integer matchMode = 1;
    private String cronExpression;
    @Min(1) @Max(3)
    private Integer priority = 2;
    @Min(0) @Max(1)
    private Integer status;
    @Size(max=8000)
    private String triggerConditions;

    public static class RssFeedItem {
        @NotBlank @Pattern(regexp="https?://[^\\s]+",message="请输入 HTTP/HTTPS 地址") @Size(max=1000)
        private String url;
        private String name;
        @Pattern(regexp="manual|system")
        private String origin;
        @Pattern(regexp="[0-9a-f]{16}")
        private String sourceId;
        @Size(max=500)
        private String reason;
        @NotBlank @Pattern(regexp="rss|web|api",message="来源类型必须为 rss、web 或 api")
        private String platform;

        public String getUrl() { return url; }
        public void setUrl(String url) { this.url = url; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getPlatform() { return platform; }
        public void setPlatform(String platform) { this.platform = platform; }
        public String getOrigin() { return origin; }
        public void setOrigin(String origin) { this.origin = origin; }
        public String getSourceId() { return sourceId; }
        public void setSourceId(String sourceId) { this.sourceId = sourceId; }
        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
    }
}
