package org.ibo.nexusjava.modules.notification.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.notification.service.NotificationService;
import org.ibo.nexusjava.modules.notification.vo.NotificationVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/java/notifications")
public class NotificationController {

    @Autowired
    private NotificationService notificationService;

    @GetMapping
    public Result<IPage<NotificationVO>> list(
            @RequestParam Long userId,
            @RequestParam(required = false, defaultValue = "1") Long current,
            @RequestParam(required = false, defaultValue = "10") Long size) {
        return Result.success(notificationService.listByUser(userId, current, size));
    }

    @GetMapping("/unread-count")
    public Result<Long> unreadCount(@RequestParam Long userId) {
        return Result.success(notificationService.countUnread(userId));
    }

    @PostMapping("/{id}/read")
    public Result<Void> markAsRead(@PathVariable Long id) {
        notificationService.markAsRead(id);
        return Result.success();
    }

    @PostMapping("/read-all")
    public Result<Void> markAllAsRead(@RequestParam Long userId) {
        notificationService.markAllAsRead(userId);
        return Result.success();
    }
}
