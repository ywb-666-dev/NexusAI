package org.ibo.nexusjava.modules.approval.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.modules.approval.dto.ApprovalTicketDTO;
import org.ibo.nexusjava.modules.approval.vo.ApprovalTicketVO;

public interface ApprovalTicketService {
    IPage<ApprovalTicketVO> listPending(Long current, Long size);
    ApprovalTicketVO getById(Long id);
    void approve(Long id, ApprovalTicketDTO dto);
    void reject(Long id, ApprovalTicketDTO dto);
}
