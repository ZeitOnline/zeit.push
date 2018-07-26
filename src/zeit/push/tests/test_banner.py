# coding: utf-8
from zeit.cms.checkout.helper import checked_out
from zeit.cms.checkout.interfaces import ICheckoutManager
from zeit.cms.content.interfaces import ISemanticChange
import lxml.etree
import transaction
import zeit.content.article.testing
import zeit.push.banner
import zeit.push.testing
import zope.security.management


class StaticArticlePublisherTest(zeit.push.testing.TestCase):

    def setUp(self):
        super(StaticArticlePublisherTest, self).setUp()
        self.repository['banner'] = zeit.content.rawxml.rawxml.RawXML()
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(
            self.repository['banner']))
        self.publisher = zeit.push.banner.homepage_banner()
        self.repository['foo'] = zeit.content.article.testing.create_article()

    def test_updates_last_semantic_change(self):
        before = ISemanticChange(
            self.repository['banner']
            ).last_semantic_change
        self.publisher.send('mytext', 'http://xml.zeit.de/homepage-banner')
        after = ISemanticChange(
            self.repository['banner']
            ).last_semantic_change
        self.assertGreater(after, before)

    def test_banner_is_updated_on_push(self):
        self.publisher.send(u'text', 'http://zeit.de/foo')
        banner = self.repository['banner']
        self.assertTrue('http://zeit.de/foo' in
                        lxml.etree.tostring(banner.xml))
        self.assertTrue('text' in
                        lxml.etree.tostring(banner.xml))

    def test_regression_handles_unicode(self):
        self.publisher.send(u'mütext', 'http://zeit.de/foo')
        banner = self.repository['banner']
        self.assertTrue('m&#252;text' in
                        lxml.etree.tostring(banner.xml))

    def test_checked_out_already_deletes_from_workingcopy_first(self):
        ICheckoutManager(self.repository['banner']).checkout()
        self.publisher.send('mytext', 'http://zeit.de/foo')

    def test_checked_out_by_somebody_else_steals_lock_first(self):
        zope.security.management.endInteraction()
        zeit.cms.testing.create_interaction('other')
        ICheckoutManager(self.repository['banner']).checkout()
        zope.security.management.endInteraction()
        zeit.cms.testing.create_interaction('zope.user')
        self.publisher.send('mytext', 'http://zeit.de/foo')

    def test_disables_message_config_only_on_commit(self):
        content = self.repository['testcontent']
        with checked_out(content) as co:
            push = zeit.push.interfaces.IPushMessages(co)
            push.short_text = u'banner'
            push.set({'type': 'homepage'}, enabled=True)
        push = zeit.push.interfaces.IPushMessages(content)
        push.messages[0].send()
        transaction.abort()
        self.assertEqual(True, push.get(type='homepage')['enabled'])
        push.messages[0].send()
        transaction.commit()
        self.assertEqual(False, push.get(type='homepage')['enabled'])
