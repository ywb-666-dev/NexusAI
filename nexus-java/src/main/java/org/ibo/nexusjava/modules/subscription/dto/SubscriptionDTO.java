package org.ibo.nexusjava.modules.subscription.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionDTO {
    @NotBlank(message = "规则名称不能为空")
    private String name;
    private List<String> keywords;
    private List<String> sourcePlatforms;
    private List<RssFeedItem> rssFeeds;
    private Integer matchMode;
    private String cronExpression;
    private Integer priority;

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
