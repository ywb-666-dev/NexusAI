package org.ibo.nexusjava.modules.content.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Data
public class ContentVO {
    private UUID id;
    private Long subscriptionId;
    private String subscriptionName;    // 关联查询订阅名称，前端展示用
    private String sourcePlatform;
    private String sourceUrl;
    private String title;
    private String summary;
    private String author;
    private LocalDateTime publishedAt;
    private LocalDateTime fetchedAt;
    private Integer isDuplicate;
    private UUID duplicateOf;
    private List<String> relatedContents; // JSON 反序列化后的数组
    private LocalDateTime createdAt;
}