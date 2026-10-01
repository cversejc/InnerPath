export default {
  async saveCourseProgress(course) { if (!this.detailUser) return; try { await updateAdminUserCourseProgress(this.detailUser.id, course.course_id, { completed_lessons: Math.min(course.completed_lessons, course.total_lessons), progress_percentage: Math.max(0, Math.min(100, Number(course.progress) || 0)), last_lesson_id: course.last_lesson_id || null }); this.message = '课程进度已保存'; await this.setUserPanelTab('courses') } catch (error) { this.message = this.errorText(error) } }
}
