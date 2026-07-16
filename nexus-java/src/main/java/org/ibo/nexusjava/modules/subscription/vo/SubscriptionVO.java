package org.ibo.nexusjava.modules.subscription.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionVO {
    private Long id;
    private String name;
    private List<String> keywords;
    private List<String> sourcePlatforms;
    private List<RssFeedItem> rssFeeds;
    private Integer matchMode;
    private String triggerConditions;
    private Integer priority;
    private Integer status;
    private String cronExpression;
    private LocalDateTime lastRunAt;
    private LocalDateTime createdAt;

    static class RssFeedItem {
        private String url;
        private String name;
        private String platform;

        public String getUrl() { return url; }
        public void setUrl(String url) { this.url = url; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getPlatform() { return platform; }
        public void setPlatform(String platform) { this.platform = platform; }
    }
}
