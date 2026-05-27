package org.ibo.nexusjava.modules.content.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.modules.content.vo.ContentVO;

public interface ContentService {
    IPage<ContentVO> listBySubscription(Long subscriptionId, Long current, Long size);
    ContentVO getById(String id);
}