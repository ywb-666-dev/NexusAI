package org.ibo.nexusjava.modules.subscription.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionDTO;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionQueryDTO;
import org.ibo.nexusjava.modules.subscription.vo.SubscriptionVO;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
public interface SubscriptionService {
    void create(SubscriptionDTO dto);
    void update(Long id, SubscriptionDTO dto);
    void delete(Long id);
    SubscriptionVO getById(Long id);
    IPage<SubscriptionVO> list(SubscriptionQueryDTO query);
    void trigger(Long id);
}