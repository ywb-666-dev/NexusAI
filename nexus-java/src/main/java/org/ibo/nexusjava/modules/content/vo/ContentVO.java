package org.ibo.nexusjava.modules.content.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ContentVO {
    private String id;
    private Long subscriptionId;
    private String subscriptionName;
    private String sourcePlatform;
    private String sourceUrl;
    private String title;
    private String summary;
    private String contentBody;
    private String author;
    private LocalDateTime publishedAt;
    private LocalDateTime fetchedAt;
    private Integer isDuplicate;
    private String duplicateOf;
    private List<String> relatedContents; // JSON 反序列化后的数组
    private LocalDateTime createdAt;
}